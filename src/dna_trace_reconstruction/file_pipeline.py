"""End-to-end synthetic DNA file recovery orchestration.

This module connects the reversible file codec to the IDS simulator and the
source-free reconstruction algorithms.  It deliberately keeps fragment order
and read-cluster identity as out-of-band metadata: clustering and DNA address
recovery are important production layers, but they are not solved here.

The original fragment sequence is retained only in :class:`FragmentRecovery`
so controlled simulations can report accuracy.  Candidate reconstruction is
isolated in :func:`reconstruct_fragment`, whose inputs contain observed traces
but no source sequence, original bytes, or expected digest.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Real

from dna_trace_reconstruction.constraints import (
    constrained_local_search,
    evidence_local_search,
)
from dna_trace_reconstruction.file_codec import (
    FileCodecError,
    decode_file_from_constrained_dna,
    encode_file_to_constrained_dna,
)
from dna_trace_reconstruction.ids_channel import generate_trace_cluster
from dna_trace_reconstruction.metrics import levenshtein_distance, normalized_edit_distance
from dna_trace_reconstruction.reconstruction import reconstruct_consensus, trace_medoid

DEFAULT_FRAGMENT_BASES = 64
DEFAULT_CLUSTER_SIZE = 11
DEFAULT_ERROR_PROBABILITY = 0.01
DEFAULT_ENCODING = "constrained-1bit-v1"
ROUTING_METADATA = "out-of-band-fragment-index"
SUPPORTED_DECODERS = ("consensus", "medoid", "evidence", "biology", "learned")


@dataclass(frozen=True, slots=True)
class FileRecoveryConfig:
    """All parameters needed to reproduce one file recovery simulation."""

    encoding: str
    routing_metadata: str
    fragment_bases: int
    cluster_size: int
    insertion_probability: float
    deletion_probability: float
    substitution_probability: float
    seed: int
    decoder: str
    consensus_rounds: int
    local_search_steps: int
    lambda_gc: float
    lambda_homopolymer: float


@dataclass(frozen=True, slots=True)
class FragmentRecovery:
    """Observed evidence, reconstruction, and benchmark metrics for one fragment.

    ``source`` is synthetic ground truth exposed only for evaluation.  It is
    never passed to :func:`reconstruct_fragment` or used to select a candidate.
    ``index`` is the fragment's out-of-band routing metadata.
    """

    index: int
    source: str
    traces: tuple[str, ...]
    reconstructed: str
    selected_method: str
    model_version: str | None
    candidate_variants: int | None
    exact: bool
    edit_distance: int
    normalized_edit_distance: float


@dataclass(frozen=True, slots=True)
class FileRecoveryResult:
    """Complete result of encoding, sequencing, and recovering one file."""

    filename: str | None
    media_type: str | None
    original_sha256: str
    original_size_bytes: int
    encoded_nucleotides: int
    fragment_count: int
    fragments: tuple[FragmentRecovery, ...]
    recovered_data: bytes | None
    recovered_filename: str | None
    recovered_media_type: str | None
    recovered_sha256: str | None
    checksum_verified: bool
    error: str | None
    config: FileRecoveryConfig

    @property
    def exact_fragment_count(self) -> int:
        """Return how many reconstructed fragments equal synthetic ground truth."""
        return sum(fragment.exact for fragment in self.fragments)

    @property
    def exact_file_recovery(self) -> bool:
        """Return whether integrity-verified recovered bytes match the input payload."""
        return self.checksum_verified and self.recovered_data is not None


def _validate_integer(name: str, value: int, *, minimum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _validated_probability(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    converted = float(value)
    if not math.isfinite(converted) or not 0.0 <= converted <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return converted


def _validated_weight(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def _validated_decoder(decoder: str) -> str:
    if not isinstance(decoder, str):
        raise TypeError("decoder must be a string")
    normalized = decoder.strip().lower()
    if normalized not in SUPPORTED_DECODERS:
        choices = ", ".join(SUPPORTED_DECODERS)
        raise ValueError(f"decoder must be one of: {choices}")
    return normalized


def reconstruct_fragment(
    traces: Iterable[str],
    *,
    decoder: str = "consensus",
    consensus_rounds: int = 5,
    local_search_steps: int = 4,
    lambda_gc: float = 1.0,
    lambda_homopolymer: float = 1.0,
) -> str:
    """Reconstruct one fragment using only its observed read cluster.

    ``evidence`` starts from alignment consensus and applies substitution-only
    evidence optimization. ``biology`` uses the same neighborhood plus the
    project's transparent GC/homopolymer penalties.  Neither mode receives
    synthetic ground truth or an expected checksum.
    """
    sequence, _, _, _ = _reconstruct_fragment_with_metadata(
        traces,
        decoder=decoder,
        consensus_rounds=consensus_rounds,
        local_search_steps=local_search_steps,
        lambda_gc=lambda_gc,
        lambda_homopolymer=lambda_homopolymer,
    )
    return sequence


def _reconstruct_fragment_with_metadata(
    traces: Iterable[str],
    *,
    decoder: str,
    consensus_rounds: int,
    local_search_steps: int,
    lambda_gc: float,
    lambda_homopolymer: float,
) -> tuple[str, str, str | None, int | None]:
    """Return sequence, selected method, model version, and candidate diversity."""
    selected_decoder = _validated_decoder(decoder)
    _validate_integer("consensus_rounds", consensus_rounds, minimum=1)
    _validate_integer("local_search_steps", local_search_steps, minimum=0)
    validated_lambda_gc = _validated_weight("lambda_gc", lambda_gc)
    validated_lambda_homopolymer = _validated_weight("lambda_homopolymer", lambda_homopolymer)

    if isinstance(traces, (str, bytes)):
        raise TypeError("traces must be an iterable of DNA strings, not one string")
    try:
        cluster = tuple(traces)
    except TypeError as error:
        raise TypeError("traces must be an iterable of DNA strings") from error

    if selected_decoder == "medoid":
        return trace_medoid(cluster), "medoid", None, None

    medoid = trace_medoid(cluster) if selected_decoder == "learned" else None
    consensus = reconstruct_consensus(cluster, max_rounds=consensus_rounds)
    if selected_decoder == "consensus":
        return consensus, "consensus", None, None

    evidence = evidence_local_search(
        consensus,
        cluster,
        max_iterations=local_search_steps,
    )
    if selected_decoder == "evidence":
        return evidence, "unconstrained", None, None

    biology = constrained_local_search(
        consensus,
        cluster,
        lambda_gc=validated_lambda_gc,
        lambda_homopolymer=validated_lambda_homopolymer,
        max_iterations=local_search_steps,
    )
    if selected_decoder == "biology":
        return biology, "constrained", None, None

    from dna_trace_reconstruction.learned_reranker import rerank_candidates

    candidate_sequences = {
        "medoid": medoid,
        "consensus": consensus,
        "unconstrained": evidence,
        "constrained": biology,
    }
    learned = rerank_candidates(cluster, candidate_sequences)
    return (
        learned.selected_sequence,
        learned.selected_name,
        learned.model_version,
        len(set(candidate_sequences.values())),
    )


def run_file_recovery(
    data: bytes | bytearray | memoryview,
    filename: str | None = None,
    media_type: str | None = None,
    *,
    fragment_bases: int = DEFAULT_FRAGMENT_BASES,
    cluster_size: int = DEFAULT_CLUSTER_SIZE,
    insertion_probability: float = DEFAULT_ERROR_PROBABILITY,
    deletion_probability: float = DEFAULT_ERROR_PROBABILITY,
    substitution_probability: float = DEFAULT_ERROR_PROBABILITY,
    seed: int = 42,
    decoder: str = "consensus",
    consensus_rounds: int = 5,
    local_search_steps: int = 4,
    lambda_gc: float = 1.0,
    lambda_homopolymer: float = 1.0,
) -> FileRecoveryResult:
    """Run a controlled file-to-DNA-to-file recovery simulation.

    The constrained codec maps one bit per nucleotide.  Its output is split
    directly into fixed-size payload fragments, avoiding the much larger
    self-indexing oligo header used by the standalone codec.  Fragment order
    and cluster identity are therefore explicit out-of-band assumptions.

    A malformed reconstruction is returned as a normal result with
    ``checksum_verified=False`` and a readable ``error`` instead of raising.
    Invalid caller inputs still raise ``TypeError`` or ``ValueError``.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("data must be bytes-like")
    payload = bytes(data)

    _validate_integer("fragment_bases", fragment_bases, minimum=8)
    if fragment_bases % 8:
        raise ValueError("fragment_bases must be divisible by 8 for constrained encoding")
    _validate_integer("cluster_size", cluster_size, minimum=1)
    _validate_integer("seed", seed, minimum=0)
    _validate_integer("consensus_rounds", consensus_rounds, minimum=1)
    _validate_integer("local_search_steps", local_search_steps, minimum=0)
    selected_decoder = _validated_decoder(decoder)
    validated_insertion = _validated_probability("insertion_probability", insertion_probability)
    validated_deletion = _validated_probability("deletion_probability", deletion_probability)
    validated_substitution = _validated_probability(
        "substitution_probability", substitution_probability
    )
    if validated_insertion + validated_deletion + validated_substitution > 1.0:
        raise ValueError("the sum of IDS probabilities cannot exceed 1")
    if validated_insertion == 1.0:
        raise ValueError("insertion_probability must be less than 1 so the channel terminates")
    validated_lambda_gc = _validated_weight("lambda_gc", lambda_gc)
    validated_lambda_homopolymer = _validated_weight("lambda_homopolymer", lambda_homopolymer)

    encoded = encode_file_to_constrained_dna(
        payload,
        filename=filename,
        media_type=media_type,
    )
    source_fragments = tuple(
        encoded[offset : offset + fragment_bases]
        for offset in range(0, len(encoded), fragment_bases)
    )
    rng = random.Random(seed)
    recovered_fragments: list[FragmentRecovery] = []

    for index, source in enumerate(source_fragments):
        traces = tuple(
            generate_trace_cluster(
                sequence=source,
                cluster_size=cluster_size,
                insertion_probability=validated_insertion,
                deletion_probability=validated_deletion,
                substitution_probability=validated_substitution,
                rng=rng,
            )
        )
        reconstructed, selected_method, model_version, candidate_variants = (
            _reconstruct_fragment_with_metadata(
                traces,
                decoder=selected_decoder,
                consensus_rounds=consensus_rounds,
                local_search_steps=local_search_steps,
                lambda_gc=validated_lambda_gc,
                lambda_homopolymer=validated_lambda_homopolymer,
            )
        )
        distance = levenshtein_distance(source, reconstructed)
        recovered_fragments.append(
            FragmentRecovery(
                index=index,
                source=source,
                traces=traces,
                reconstructed=reconstructed,
                selected_method=selected_method,
                model_version=model_version,
                candidate_variants=candidate_variants,
                exact=reconstructed == source,
                edit_distance=distance,
                normalized_edit_distance=normalized_edit_distance(source, reconstructed),
            )
        )

    reconstructed_dna = "".join(fragment.reconstructed for fragment in recovered_fragments)
    original_sha256 = hashlib.sha256(payload).hexdigest()
    recovered_data: bytes | None = None
    recovered_filename: str | None = None
    recovered_media_type: str | None = None
    recovered_sha256: str | None = None
    checksum_verified = False
    recovery_error: str | None = None

    try:
        decoded = decode_file_from_constrained_dna(reconstructed_dna)
    except FileCodecError as error:
        recovery_error = f"File recovery failed integrity or format validation: {error}"
    else:
        recovered_data = decoded.data
        recovered_filename = decoded.filename
        recovered_media_type = decoded.media_type
        recovered_sha256 = decoded.sha256
        checksum_verified = decoded.sha256 == original_sha256 and decoded.data == payload
        if not checksum_verified:
            recovery_error = (
                "Recovered data passed its embedded integrity check but does not match "
                "the original simulation payload."
            )

    config = FileRecoveryConfig(
        encoding=DEFAULT_ENCODING,
        routing_metadata=ROUTING_METADATA,
        fragment_bases=fragment_bases,
        cluster_size=cluster_size,
        insertion_probability=validated_insertion,
        deletion_probability=validated_deletion,
        substitution_probability=validated_substitution,
        seed=seed,
        decoder=selected_decoder,
        consensus_rounds=consensus_rounds,
        local_search_steps=local_search_steps,
        lambda_gc=validated_lambda_gc,
        lambda_homopolymer=validated_lambda_homopolymer,
    )
    fragments = tuple(recovered_fragments)
    return FileRecoveryResult(
        filename=filename,
        media_type=media_type,
        original_sha256=original_sha256,
        original_size_bytes=len(payload),
        encoded_nucleotides=len(encoded),
        fragment_count=len(fragments),
        fragments=fragments,
        recovered_data=recovered_data,
        recovered_filename=recovered_filename,
        recovered_media_type=recovered_media_type,
        recovered_sha256=recovered_sha256,
        checksum_verified=checksum_verified,
        error=recovery_error,
        config=config,
    )
