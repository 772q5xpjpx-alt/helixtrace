"""End-to-end experiment orchestration for HelixTrace."""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from dna_trace_reconstruction.constraints import (
    constrained_local_search,
    evidence_cost,
    evidence_local_search,
    summarize_biological_constraints,
)
from dna_trace_reconstruction.ids_channel import generate_trace_cluster
from dna_trace_reconstruction.metrics import levenshtein_distance, normalized_edit_distance
from dna_trace_reconstruction.reconstruction import reconstruct_consensus, trace_medoid


@dataclass(frozen=True)
class ExperimentConfig:
    """Inputs that make one synthetic reconstruction experiment reproducible."""

    cluster_size: int
    insertion_probability: float
    deletion_probability: float
    substitution_probability: float
    seed: int
    lambda_gc: float
    lambda_homopolymer: float
    local_search_steps: int


@dataclass(frozen=True)
class CandidateEvaluation:
    """Evaluation of one candidate against known synthetic ground truth."""

    label: str
    sequence: str
    edit_distance: int
    normalized_edit_distance: float
    exact_recovery: bool
    gc_fraction: float
    max_homopolymer_run: int
    gc_excess: float
    homopolymer_excess: int
    biologically_valid: bool
    evidence_cost: float


@dataclass(frozen=True)
class ReconstructionCandidates:
    """Source-free candidate sequences reconstructed from one trace cluster."""

    medoid: str
    consensus: str
    unconstrained: str
    constrained: str


@dataclass(frozen=True)
class ExperimentResult:
    """Complete, serializable output of one HelixTrace experiment."""

    source: str
    traces: tuple[str, ...]
    config: ExperimentConfig
    medoid: CandidateEvaluation
    consensus: CandidateEvaluation
    unconstrained: CandidateEvaluation
    constrained: CandidateEvaluation


def reconstruct_trace_cluster(
    traces: Iterable[str],
    *,
    lambda_gc: float = 1.0,
    lambda_homopolymer: float = 1.0,
    local_search_steps: int = 4,
) -> ReconstructionCandidates:
    """Reconstruct candidates from observed reads without access to ground truth.

    Keeping this source-free stage separate matters for file recovery: the
    original strand is unavailable outside a controlled synthetic benchmark.
    """
    cluster = tuple(traces)
    medoid_sequence = trace_medoid(cluster)
    consensus_sequence = reconstruct_consensus(cluster)
    unconstrained_sequence = evidence_local_search(
        consensus_sequence,
        cluster,
        max_iterations=local_search_steps,
    )
    constrained_sequence = constrained_local_search(
        consensus_sequence,
        cluster,
        lambda_gc=lambda_gc,
        lambda_homopolymer=lambda_homopolymer,
        max_iterations=local_search_steps,
    )
    return ReconstructionCandidates(
        medoid=medoid_sequence,
        consensus=consensus_sequence,
        unconstrained=unconstrained_sequence,
        constrained=constrained_sequence,
    )


def _evaluate_candidate(
    label: str,
    candidate: str,
    source: str,
    traces: list[str],
) -> CandidateEvaluation:
    biological = summarize_biological_constraints(candidate)
    return CandidateEvaluation(
        label=label,
        sequence=candidate,
        edit_distance=levenshtein_distance(source, candidate),
        normalized_edit_distance=normalized_edit_distance(source, candidate),
        exact_recovery=candidate == source,
        gc_fraction=biological.gc_fraction,
        max_homopolymer_run=biological.max_homopolymer_run,
        gc_excess=biological.gc_excess,
        homopolymer_excess=biological.homopolymer_excess,
        biologically_valid=biological.valid,
        evidence_cost=evidence_cost(candidate, traces),
    )


def run_experiment(
    source: str,
    *,
    cluster_size: int = 5,
    insertion_probability: float = 0.06,
    deletion_probability: float = 0.06,
    substitution_probability: float = 0.06,
    seed: int = 42,
    lambda_gc: float = 1.0,
    lambda_homopolymer: float = 1.0,
    local_search_steps: int = 4,
) -> ExperimentResult:
    """Simulate traces, reconstruct them, and evaluate three transparent baselines.

    The reconstruction functions receive only the noisy traces. The known source
    is used after reconstruction solely to calculate benchmark metrics.
    """
    normalized_source = source.strip().upper()
    traces = generate_trace_cluster(
        sequence=normalized_source,
        cluster_size=cluster_size,
        insertion_probability=insertion_probability,
        deletion_probability=deletion_probability,
        substitution_probability=substitution_probability,
        rng=random.Random(seed),
    )

    candidates = reconstruct_trace_cluster(
        traces,
        lambda_gc=lambda_gc,
        lambda_homopolymer=lambda_homopolymer,
        local_search_steps=local_search_steps,
    )

    config = ExperimentConfig(
        cluster_size=cluster_size,
        insertion_probability=insertion_probability,
        deletion_probability=deletion_probability,
        substitution_probability=substitution_probability,
        seed=seed,
        lambda_gc=lambda_gc,
        lambda_homopolymer=lambda_homopolymer,
        local_search_steps=local_search_steps,
    )
    return ExperimentResult(
        source=normalized_source,
        traces=tuple(traces),
        config=config,
        medoid=_evaluate_candidate("Trace medoid", candidates.medoid, normalized_source, traces),
        consensus=_evaluate_candidate(
            "Alignment consensus", candidates.consensus, normalized_source, traces
        ),
        unconstrained=_evaluate_candidate(
            "Evidence-only refinement", candidates.unconstrained, normalized_source, traces
        ),
        constrained=_evaluate_candidate(
            "Biology-aware decoding", candidates.constrained, normalized_source, traces
        ),
    )


def experiment_as_dict(result: ExperimentResult) -> dict[str, Any]:
    """Return a JSON-compatible representation of an experiment result."""
    return asdict(result)


def compact_experiment_payload(result: ExperimentResult) -> dict[str, Any]:
    """Return the bounded evidence sent to the GPT experiment analyst."""
    data = experiment_as_dict(result)
    return {
        "experiment_type": "controlled synthetic uncoded DNA trace reconstruction",
        "source": data["source"],
        "trace_count": len(data["traces"]),
        "trace_lengths": [len(trace) for trace in data["traces"]],
        "config": data["config"],
        "candidates": {
            key: data[key] for key in ("medoid", "consensus", "unconstrained", "constrained")
        },
        "method_note": (
            "Biology-aware decoding is deterministic post-hoc local search over substitutions. "
            "It is not a trained neural model or a differentiable-loss result."
        ),
    }
