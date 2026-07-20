"""Utilities for generating controlled synthetic DNA source strands."""

from __future__ import annotations

import random

from dna_trace_reconstruction.ids_channel import DNA_ALPHABET


def _max_homopolymer_run(sequence: str) -> int:
    if not sequence:
        return 0

    longest = 1
    current = 1
    for previous, base in zip(sequence, sequence[1:], strict=False):
        if base == previous:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def generate_constrained_source(
    length: int,
    rng: random.Random,
    *,
    minimum_gc: float = 0.45,
    maximum_gc: float = 0.55,
    maximum_homopolymer: int = 3,
    max_attempts: int = 10_000,
) -> str:
    """Generate a random strand satisfying simple DNA-storage design rules.

    Rejection sampling is intentionally used here because it keeps the source
    distribution transparent. The function is for controlled synthetic
    experiments; it is not a production DNA encoder.
    """
    if isinstance(length, bool) or not isinstance(length, int):
        raise TypeError("length must be an integer")
    if length < 1:
        raise ValueError("length must be at least 1")
    if not 0.0 <= minimum_gc <= maximum_gc <= 1.0:
        raise ValueError("GC bounds must satisfy 0 <= minimum <= maximum <= 1")
    if isinstance(maximum_homopolymer, bool) or not isinstance(maximum_homopolymer, int):
        raise TypeError("maximum_homopolymer must be an integer")
    if maximum_homopolymer < 1:
        raise ValueError("maximum_homopolymer must be at least 1")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        raise TypeError("max_attempts must be an integer")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if not hasattr(rng, "choice"):
        raise TypeError("rng must provide choice()")

    for _ in range(max_attempts):
        sequence = "".join(rng.choice(DNA_ALPHABET) for _ in range(length))
        gc_fraction = (sequence.count("G") + sequence.count("C")) / length
        if (
            minimum_gc <= gc_fraction <= maximum_gc
            and _max_homopolymer_run(sequence) <= maximum_homopolymer
        ):
            return sequence

    raise RuntimeError(
        "Could not generate a strand satisfying the requested constraints; "
        "relax the bounds or increase max_attempts"
    )
