"""Biological constraints and constraint-aware reconstruction utilities."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Real

from dna_trace_reconstruction.ids_channel import DNA_ALPHABET
from dna_trace_reconstruction.metrics import levenshtein_distance

DEFAULT_MIN_GC_FRACTION = 0.45
DEFAULT_MAX_GC_FRACTION = 0.55
DEFAULT_MAX_HOMOPOLYMER_RUN = 3


@dataclass(frozen=True, slots=True)
class BiologicalSummary:
    """A compact, explainable summary of DNA synthesis constraints.

    ``gc_excess`` is measured in bases: it is the distance between the observed
    GC count and the allowed fractional interval multiplied by sequence length.
    ``homopolymer_excess`` is the number of bases by which the longest run
    exceeds the configured maximum.
    """

    gc_fraction: float
    max_homopolymer_run: int
    gc_excess: float
    homopolymer_excess: int
    valid: bool


def _validate_dna_sequence(name: str, sequence: str) -> None:
    if not isinstance(sequence, str):
        raise TypeError(f"{name} must be a string")

    invalid_bases = sorted(set(sequence) - set(DNA_ALPHABET))
    if invalid_bases:
        raise ValueError(f"Invalid DNA bases in {name}: {invalid_bases}")


def _validate_gc_bounds(minimum: float, maximum: float) -> None:
    for name, value in (
        ("minimum_gc_fraction", minimum),
        ("maximum_gc_fraction", maximum),
    ):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{name} must be a real number")
        if not math.isfinite(value) or not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be between 0 and 1")

    if minimum > maximum:
        raise ValueError("minimum_gc_fraction cannot exceed maximum_gc_fraction")


def _validate_max_homopolymer_run(maximum_run: int) -> None:
    if isinstance(maximum_run, bool) or not isinstance(maximum_run, int):
        raise TypeError("maximum_homopolymer_run must be an integer")
    if maximum_run < 1:
        raise ValueError("maximum_homopolymer_run must be at least 1")


def _validate_weight(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")


def gc_fraction(sequence: str) -> float:
    """Return the fraction of symbols that are G or C.

    The empty sequence has fraction ``0.0``. It is nevertheless marked invalid
    by :func:`summarize_biological_constraints` because it is not a strand.
    """
    _validate_dna_sequence("sequence", sequence)
    if not sequence:
        return 0.0
    return sum(base in "GC" for base in sequence) / len(sequence)


def gc_fraction_excess(
    sequence: str,
    minimum_gc_fraction: float = DEFAULT_MIN_GC_FRACTION,
    maximum_gc_fraction: float = DEFAULT_MAX_GC_FRACTION,
) -> float:
    """Return how far the observed GC fraction lies outside an allowed range."""
    _validate_gc_bounds(minimum_gc_fraction, maximum_gc_fraction)
    observed_fraction = gc_fraction(sequence)

    if not sequence:
        return 0.0
    if observed_fraction < minimum_gc_fraction:
        return minimum_gc_fraction - observed_fraction
    if observed_fraction > maximum_gc_fraction:
        return observed_fraction - maximum_gc_fraction
    return 0.0


def gc_count_excess(
    sequence: str,
    minimum_gc_fraction: float = DEFAULT_MIN_GC_FRACTION,
    maximum_gc_fraction: float = DEFAULT_MAX_GC_FRACTION,
) -> float:
    """Return GC violation magnitude in units of nucleotide count.

    Fractional values are intentional. For example, a length-10 strand with
    four GC bases is ``0.5`` bases below a 45% lower bound.
    """
    return len(sequence) * gc_fraction_excess(
        sequence,
        minimum_gc_fraction=minimum_gc_fraction,
        maximum_gc_fraction=maximum_gc_fraction,
    )


def max_homopolymer_run(sequence: str) -> int:
    """Return the length of the longest consecutive run of one base."""
    _validate_dna_sequence("sequence", sequence)
    if not sequence:
        return 0

    longest_run = 1
    current_run = 1

    for previous_base, current_base in zip(sequence, sequence[1:], strict=False):
        if current_base == previous_base:
            current_run += 1
            longest_run = max(longest_run, current_run)
        else:
            current_run = 1

    return longest_run


def homopolymer_excess(
    sequence: str,
    maximum_homopolymer_run: int = DEFAULT_MAX_HOMOPOLYMER_RUN,
) -> int:
    """Return how many bases the longest run exceeds the configured limit."""
    _validate_max_homopolymer_run(maximum_homopolymer_run)
    return max(0, max_homopolymer_run(sequence) - maximum_homopolymer_run)


def summarize_biological_constraints(
    sequence: str,
    *,
    minimum_gc_fraction: float = DEFAULT_MIN_GC_FRACTION,
    maximum_gc_fraction: float = DEFAULT_MAX_GC_FRACTION,
    maximum_homopolymer_run: int = DEFAULT_MAX_HOMOPOLYMER_RUN,
) -> BiologicalSummary:
    """Measure GC balance and homopolymer validity for one DNA sequence."""
    _validate_gc_bounds(minimum_gc_fraction, maximum_gc_fraction)
    _validate_max_homopolymer_run(maximum_homopolymer_run)
    _validate_dna_sequence("sequence", sequence)

    observed_gc_fraction = gc_fraction(sequence)
    observed_max_run = max_homopolymer_run(sequence)
    observed_gc_excess = gc_count_excess(
        sequence,
        minimum_gc_fraction=minimum_gc_fraction,
        maximum_gc_fraction=maximum_gc_fraction,
    )
    observed_homopolymer_excess = max(
        0,
        observed_max_run - maximum_homopolymer_run,
    )

    return BiologicalSummary(
        gc_fraction=observed_gc_fraction,
        max_homopolymer_run=observed_max_run,
        gc_excess=observed_gc_excess,
        homopolymer_excess=observed_homopolymer_excess,
        valid=(bool(sequence) and observed_gc_excess == 0.0 and observed_homopolymer_excess == 0),
    )


def is_biologically_valid(
    sequence: str,
    *,
    minimum_gc_fraction: float = DEFAULT_MIN_GC_FRACTION,
    maximum_gc_fraction: float = DEFAULT_MAX_GC_FRACTION,
    maximum_homopolymer_run: int = DEFAULT_MAX_HOMOPOLYMER_RUN,
) -> bool:
    """Return whether one non-empty sequence meets all configured constraints."""
    return summarize_biological_constraints(
        sequence,
        minimum_gc_fraction=minimum_gc_fraction,
        maximum_gc_fraction=maximum_gc_fraction,
        maximum_homopolymer_run=maximum_homopolymer_run,
    ).valid


def _validated_traces(traces: Sequence[str]) -> tuple[str, ...]:
    if isinstance(traces, (str, bytes)) or not isinstance(traces, Sequence):
        raise TypeError("traces must be a sequence of strings")
    if not traces:
        raise ValueError("traces must contain at least one sequence")

    validated = tuple(traces)
    for index, trace in enumerate(validated):
        _validate_dna_sequence(f"traces[{index}]", trace)
    return validated


def evidence_cost(candidate: str, traces: Sequence[str]) -> float:
    """Return mean Levenshtein distance from a candidate to observed traces."""
    _validate_dna_sequence("candidate", candidate)
    validated_traces = _validated_traces(traces)
    total_distance = sum(levenshtein_distance(candidate, trace) for trace in validated_traces)
    return total_distance / len(validated_traces)


def reconstruction_objective(
    candidate: str,
    traces: Sequence[str],
    *,
    lambda_gc: float = 0.0,
    lambda_homopolymer: float = 0.0,
    minimum_gc_fraction: float = DEFAULT_MIN_GC_FRACTION,
    maximum_gc_fraction: float = DEFAULT_MAX_GC_FRACTION,
    maximum_homopolymer_run: int = DEFAULT_MAX_HOMOPOLYMER_RUN,
) -> float:
    """Combine trace evidence with soft, explainable biological penalties."""
    _validate_weight("lambda_gc", lambda_gc)
    _validate_weight("lambda_homopolymer", lambda_homopolymer)
    summary = summarize_biological_constraints(
        candidate,
        minimum_gc_fraction=minimum_gc_fraction,
        maximum_gc_fraction=maximum_gc_fraction,
        maximum_homopolymer_run=maximum_homopolymer_run,
    )
    return (
        evidence_cost(candidate, traces)
        + lambda_gc * summary.gc_excess
        + lambda_homopolymer * summary.homopolymer_excess
    )


def objective(
    candidate: str,
    traces: Sequence[str],
    **kwargs: float | int,
) -> float:
    """Alias for :func:`reconstruction_objective`."""
    return reconstruction_objective(candidate, traces, **kwargs)


def evidence_local_search(
    initial_sequence: str,
    traces: Sequence[str],
    *,
    max_iterations: int | None = None,
) -> str:
    """Refine a candidate using trace evidence alone.

    This control uses exactly the same deterministic substitution neighborhood
    as :func:`constrained_local_search`, but its objective contains no
    biological penalties. Comparing both searches isolates the effect of the
    biological prior from the effect of simply doing more optimization.
    """
    _validate_dna_sequence("initial_sequence", initial_sequence)
    validated_traces = _validated_traces(traces)

    if max_iterations is not None:
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
            raise TypeError("max_iterations must be an integer or None")
        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")

    if not initial_sequence or max_iterations == 0:
        return initial_sequence

    iteration_limit = max_iterations
    if iteration_limit is None:
        iteration_limit = max(1, len(initial_sequence) * len(DNA_ALPHABET))

    current = initial_sequence
    current_cost = evidence_cost(current, validated_traces)

    for _ in range(iteration_limit):
        best_sequence = current
        best_cost = current_cost

        for position, original_base in enumerate(current):
            for replacement in DNA_ALPHABET:
                if replacement == original_base:
                    continue
                candidate = current[:position] + replacement + current[position + 1 :]
                candidate_cost = evidence_cost(candidate, validated_traces)

                if candidate_cost < best_cost or (
                    math.isclose(candidate_cost, best_cost, abs_tol=1e-12)
                    and candidate_cost < current_cost
                    and candidate < best_sequence
                ):
                    best_sequence = candidate
                    best_cost = candidate_cost

        if best_sequence == current:
            break

        current = best_sequence
        current_cost = best_cost

    return current


def constrained_local_search(
    initial_sequence: str,
    traces: Sequence[str],
    *,
    lambda_gc: float = 1.0,
    lambda_homopolymer: float = 1.0,
    minimum_gc_fraction: float = DEFAULT_MIN_GC_FRACTION,
    maximum_gc_fraction: float = DEFAULT_MAX_GC_FRACTION,
    maximum_homopolymer_run: int = DEFAULT_MAX_HOMOPOLYMER_RUN,
    max_iterations: int | None = None,
) -> str:
    """Improve the reconstruction objective with deterministic substitutions.

    The search uses best-improvement hill climbing. It considers every
    one-base substitution, accepts the lowest-cost strict improvement, and
    breaks equal-cost ties lexicographically. It never inserts or deletes a
    base, so the returned sequence always has the initial length.

    With both penalty weights set to zero the function deliberately returns the
    initial sequence unchanged; unconstrained reconstruction is handled by the
    upstream consensus algorithm.
    """
    _validate_dna_sequence("initial_sequence", initial_sequence)
    validated_traces = _validated_traces(traces)
    _validate_weight("lambda_gc", lambda_gc)
    _validate_weight("lambda_homopolymer", lambda_homopolymer)
    _validate_gc_bounds(minimum_gc_fraction, maximum_gc_fraction)
    _validate_max_homopolymer_run(maximum_homopolymer_run)

    if max_iterations is not None:
        if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
            raise TypeError("max_iterations must be an integer or None")
        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")

    if lambda_gc == 0.0 and lambda_homopolymer == 0.0:
        return initial_sequence

    if not initial_sequence or max_iterations == 0:
        return initial_sequence

    iteration_limit = max_iterations
    if iteration_limit is None:
        iteration_limit = max(1, len(initial_sequence) * len(DNA_ALPHABET))

    objective_kwargs = {
        "lambda_gc": lambda_gc,
        "lambda_homopolymer": lambda_homopolymer,
        "minimum_gc_fraction": minimum_gc_fraction,
        "maximum_gc_fraction": maximum_gc_fraction,
        "maximum_homopolymer_run": maximum_homopolymer_run,
    }
    current = initial_sequence
    current_cost = reconstruction_objective(
        current,
        validated_traces,
        **objective_kwargs,
    )

    for _ in range(iteration_limit):
        best_sequence = current
        best_cost = current_cost

        for position, original_base in enumerate(current):
            for replacement in DNA_ALPHABET:
                if replacement == original_base:
                    continue
                candidate = current[:position] + replacement + current[position + 1 :]
                candidate_cost = reconstruction_objective(
                    candidate,
                    validated_traces,
                    **objective_kwargs,
                )

                if candidate_cost < best_cost or (
                    math.isclose(candidate_cost, best_cost, abs_tol=1e-12)
                    and candidate_cost < current_cost
                    and candidate < best_sequence
                ):
                    best_sequence = candidate
                    best_cost = candidate_cost

        if best_sequence == current:
            break

        current = best_sequence
        current_cost = best_cost

    return current
