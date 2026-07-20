import random

import pytest

from dna_trace_reconstruction.source_design import generate_constrained_source


def test_generate_constrained_source_is_valid_and_reproducible():
    first = generate_constrained_source(80, random.Random(7))
    second = generate_constrained_source(80, random.Random(7))

    assert first == second
    assert len(first) == 80
    assert set(first) <= set("ACGT")
    gc_fraction = (first.count("G") + first.count("C")) / len(first)
    assert 0.45 <= gc_fraction <= 0.55
    assert all(base * 4 not in first for base in "ACGT")


@pytest.mark.parametrize("length", [0, -1])
def test_generate_constrained_source_rejects_invalid_length(length):
    with pytest.raises(ValueError, match="at least 1"):
        generate_constrained_source(length, random.Random(1))


def test_generate_constrained_source_rejects_impossible_attempt_budget():
    with pytest.raises(RuntimeError, match="Could not generate"):
        generate_constrained_source(
            1,
            random.Random(1),
            minimum_gc=0.5,
            maximum_gc=0.5,
            max_attempts=2,
        )
