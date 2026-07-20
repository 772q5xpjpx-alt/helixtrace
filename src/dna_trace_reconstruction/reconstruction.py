"""Deterministic alignment-aware consensus reconstruction for DNA traces.

The implementation is intentionally small and dependency-free.  It uses a
trace medoid as an order-independent starting point, aligns every trace to the
current reference, and then votes separately on reference bases and insertion
boundaries.  Repeating that process lets the reference length change while
remaining deterministic.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from .ids_channel import DNA_ALPHABET
from .metrics import levenshtein_distance


@dataclass(frozen=True)
class AlignmentCalls:
    """Trace evidence expressed relative to one ungapped reference.

    ``insertions`` has one entry for every reference boundary, including the
    boundary before the first base and the one after the final base. ``bases``
    contains either a called DNA base or ``"-"`` for each reference position.
    """

    insertions: tuple[str, ...]
    bases: tuple[str, ...]


def _validate_dna(sequence: str, *, name: str) -> None:
    if not isinstance(sequence, str):
        raise TypeError(f"{name} must be a string")

    invalid_bases = sorted(set(sequence) - set(DNA_ALPHABET))
    if invalid_bases:
        raise ValueError(f"{name} contains invalid DNA bases: {invalid_bases}")


def _validated_traces(traces: Iterable[str]) -> tuple[str, ...]:
    if isinstance(traces, (str, bytes)):
        raise TypeError("traces must be an iterable of DNA strings, not one string")

    try:
        cluster = tuple(traces)
    except TypeError as error:
        raise TypeError("traces must be an iterable of DNA strings") from error

    if not cluster:
        raise ValueError("traces must contain at least one DNA trace")

    for index, trace in enumerate(cluster):
        _validate_dna(trace, name=f"traces[{index}]")

    return cluster


def global_align(reference: str, trace: str) -> tuple[str, str]:
    """Return a deterministic unit-cost global alignment.

    Matches cost zero; substitutions, insertions, and deletions each cost one.
    When several optimal paths exist, diagonal moves are preferred, followed
    by a gap in the trace and then a gap in the reference.  That explicit
    policy makes ambiguous alignments reproducible.
    """

    _validate_dna(reference, name="reference")
    _validate_dna(trace, name="trace")

    reference_length = len(reference)
    trace_length = len(trace)
    distances = [[0] * (trace_length + 1) for _ in range(reference_length + 1)]

    for reference_index in range(1, reference_length + 1):
        distances[reference_index][0] = reference_index
    for trace_index in range(1, trace_length + 1):
        distances[0][trace_index] = trace_index

    for reference_index in range(1, reference_length + 1):
        for trace_index in range(1, trace_length + 1):
            substitution_cost = reference[reference_index - 1] != trace[trace_index - 1]
            distances[reference_index][trace_index] = min(
                distances[reference_index - 1][trace_index - 1] + substitution_cost,
                distances[reference_index - 1][trace_index] + 1,
                distances[reference_index][trace_index - 1] + 1,
            )

    aligned_reference: list[str] = []
    aligned_trace: list[str] = []
    reference_index = reference_length
    trace_index = trace_length

    while reference_index or trace_index:
        if reference_index and trace_index:
            substitution_cost = reference[reference_index - 1] != trace[trace_index - 1]
            if (
                distances[reference_index][trace_index]
                == distances[reference_index - 1][trace_index - 1] + substitution_cost
            ):
                aligned_reference.append(reference[reference_index - 1])
                aligned_trace.append(trace[trace_index - 1])
                reference_index -= 1
                trace_index -= 1
                continue

        if reference_index and (
            distances[reference_index][trace_index]
            == distances[reference_index - 1][trace_index] + 1
        ):
            aligned_reference.append(reference[reference_index - 1])
            aligned_trace.append("-")
            reference_index -= 1
            continue

        aligned_reference.append("-")
        aligned_trace.append(trace[trace_index - 1])
        trace_index -= 1

    return (
        "".join(reversed(aligned_reference)),
        "".join(reversed(aligned_trace)),
    )


def parse_alignment(aligned_reference: str, aligned_trace: str) -> AlignmentCalls:
    """Parse an alignment into insertion-boundary and base/gap calls."""

    if not isinstance(aligned_reference, str) or not isinstance(aligned_trace, str):
        raise TypeError("aligned sequences must be strings")
    if len(aligned_reference) != len(aligned_trace):
        raise ValueError("aligned sequences must have equal length")

    allowed_symbols = set(DNA_ALPHABET) | {"-"}
    for name, sequence in (
        ("aligned_reference", aligned_reference),
        ("aligned_trace", aligned_trace),
    ):
        invalid_symbols = sorted(set(sequence) - allowed_symbols)
        if invalid_symbols:
            raise ValueError(f"{name} contains invalid symbols: {invalid_symbols}")

    reference_length = sum(symbol != "-" for symbol in aligned_reference)
    insertions: list[list[str]] = [[] for _ in range(reference_length + 1)]
    bases: list[str] = []
    boundary = 0

    for reference_symbol, trace_symbol in zip(aligned_reference, aligned_trace, strict=True):
        if reference_symbol == "-":
            if trace_symbol == "-":
                raise ValueError("an alignment column cannot contain two gaps")
            insertions[boundary].append(trace_symbol)
            continue

        bases.append(trace_symbol)
        boundary += 1

    return AlignmentCalls(
        insertions=tuple("".join(call) for call in insertions),
        bases=tuple(bases),
    )


def _sequence_medoid(sequences: Iterable[str], *, prefer_shorter: bool) -> str:
    samples = tuple(sequences)
    candidates = sorted(set(samples))

    def candidate_key(candidate: str) -> tuple[int, int, str] | tuple[int, str]:
        total_distance = sum(levenshtein_distance(candidate, sample) for sample in samples)
        if prefer_shorter:
            return total_distance, len(candidate), candidate
        return total_distance, candidate

    return min(candidates, key=candidate_key)


def trace_medoid(traces: Iterable[str]) -> str:
    """Return the trace with minimum total distance to the cluster.

    Duplicate traces retain their statistical weight. Ties are broken
    lexicographically, so permuting the input cluster cannot change the result.
    """

    cluster = _validated_traces(traces)
    return _sequence_medoid(cluster, prefer_shorter=False)


def _boundary_medoid(calls: Iterable[str]) -> str:
    """Choose observed insertion evidence, preferring shorter calls in ties."""

    return _sequence_medoid(calls, prefer_shorter=True)


def _base_consensus(reference_base: str, calls: Iterable[str]) -> str:
    counts = Counter(calls)
    maximum_count = max(counts.values())
    tied_calls = {call for call, count in counts.items() if count == maximum_count}

    if reference_base in tied_calls:
        return reference_base

    called_bases = sorted(tied_calls - {"-"})
    if called_bases:
        return called_bases[0]
    return "-"


def consensus_round(reference: str, traces: Iterable[str]) -> str:
    """Run one alignment-aware consensus update against ``reference``."""

    _validate_dna(reference, name="reference")
    cluster = _validated_traces(traces)
    calls = [parse_alignment(*global_align(reference, trace)) for trace in cluster]

    reconstructed: list[str] = []
    for boundary in range(len(reference) + 1):
        reconstructed.append(_boundary_medoid(call.insertions[boundary] for call in calls))
        if boundary == len(reference):
            continue

        base_call = _base_consensus(reference[boundary], (call.bases[boundary] for call in calls))
        if base_call != "-":
            reconstructed.append(base_call)

    return "".join(reconstructed)


def _state_key(sequence: str, traces: tuple[str, ...]) -> tuple[int, int, str]:
    return (
        sum(levenshtein_distance(sequence, trace) for trace in traces),
        len(sequence),
        sequence,
    )


def reconstruct_consensus(traces: Iterable[str], max_rounds: int = 5) -> str:
    """Iteratively reconstruct one sequence from a cluster of noisy traces.

    The trace medoid initializes the reference. If alignment ambiguity produces
    a cycle, the state with the smallest total distance to all traces is
    selected; remaining ties favor the shorter, lexicographically smaller
    sequence. At the iteration limit, the latest consensus is returned.
    """

    cluster = _validated_traces(traces)
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int):
        raise TypeError("max_rounds must be an integer")
    if max_rounds < 1:
        raise ValueError("max_rounds must be at least 1")

    current = trace_medoid(cluster)
    history = [current]
    seen_at = {current: 0}

    for _ in range(max_rounds):
        updated = consensus_round(current, cluster)
        if updated == current:
            return current

        if updated in seen_at:
            cycle = history[seen_at[updated] :]
            return min(cycle, key=lambda sequence: _state_key(sequence, cluster))

        seen_at[updated] = len(history)
        history.append(updated)
        current = updated

    return current
