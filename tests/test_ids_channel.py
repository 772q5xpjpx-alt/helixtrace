import random

import pytest

from dna_trace_reconstruction.ids_channel import (
    DNA_ALPHABET,
    generate_trace_cluster,
    simulate_ids_channel,
)


class ScriptedRandom:
    """Minimal deterministic random source for testing channel transitions."""

    def __init__(self, events, choices=()):
        self._events = iter(events)
        self._choices = iter(choices)

    def random(self):
        return next(self._events)

    def choice(self, population):
        choice = next(self._choices)
        assert choice in population
        return choice


def simulate(sequence, *, insertion=0.0, deletion=0.0, substitution=0.0, seed=42):
    return simulate_ids_channel(
        sequence=sequence,
        insertion_probability=insertion,
        deletion_probability=deletion,
        substitution_probability=substitution,
        rng=random.Random(seed),
    )


def test_zero_error_probabilities_preserve_sequence():
    assert simulate("ACGTACGT") == "ACGTACGT"


def test_empty_sequence_returns_empty_trace():
    assert simulate("") == ""


def test_deletion_probability_one_removes_every_base():
    assert simulate("ACGT", deletion=1.0) == ""


def test_substitution_probability_one_changes_every_base():
    source = "AACCGGTT"
    trace = simulate(source, substitution=1.0)

    assert len(trace) == len(source)
    assert all(
        source_base != trace_base for source_base, trace_base in zip(source, trace, strict=True)
    )


def test_insertion_does_not_advance_source_pointer():
    rng = ScriptedRandom(events=[0.1, 0.9], choices=["T"])

    trace = simulate_ids_channel(
        sequence="A",
        insertion_probability=0.5,
        deletion_probability=0.0,
        substitution_probability=0.0,
        rng=rng,
    )

    assert trace == "TA"


def test_scripted_channel_applies_all_three_error_types():
    rng = ScriptedRandom(
        events=[0.05, 0.95, 0.25, 0.5, 0.95],
        choices=["T", "A"],
    )

    trace = simulate_ids_channel(
        sequence="ACGT",
        insertion_probability=0.1,
        deletion_probability=0.2,
        substitution_probability=0.3,
        rng=rng,
    )

    assert trace == "TAAT"


def test_fixed_seed_produces_reproducible_results():
    parameters = {
        "sequence": "ACGTACGT",
        "insertion_probability": 0.1,
        "deletion_probability": 0.1,
        "substitution_probability": 0.1,
    }

    first_trace = simulate_ids_channel(**parameters, rng=random.Random(42))
    second_trace = simulate_ids_channel(**parameters, rng=random.Random(42))

    assert first_trace == second_trace


def test_output_contains_only_valid_dna_bases():
    trace = simulate(
        "ACGT" * 100,
        insertion=0.2,
        deletion=0.2,
        substitution=0.2,
    )

    assert set(trace) <= set(DNA_ALPHABET)


@pytest.mark.parametrize("sequence", ["ACNT", "acgt", "ACG-"])
def test_invalid_dna_bases_are_rejected(sequence):
    with pytest.raises(ValueError, match="Invalid DNA bases"):
        simulate(sequence)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("insertion_probability", -0.01),
        ("deletion_probability", 1.01),
        ("substitution_probability", float("nan")),
        ("substitution_probability", float("inf")),
    ],
)
def test_invalid_probability_values_are_rejected(field, value):
    parameters = {
        "sequence": "ACGT",
        "insertion_probability": 0.0,
        "deletion_probability": 0.0,
        "substitution_probability": 0.0,
        "rng": random.Random(42),
    }
    parameters[field] = value

    with pytest.raises(ValueError, match="must be between 0 and 1"):
        simulate_ids_channel(**parameters)


def test_non_numeric_probability_is_rejected():
    with pytest.raises(TypeError, match="must be a real number"):
        simulate_ids_channel(
            sequence="ACGT",
            insertion_probability="0.1",
            deletion_probability=0.0,
            substitution_probability=0.0,
            rng=random.Random(42),
        )


def test_probability_sum_above_one_is_rejected():
    with pytest.raises(ValueError, match="sum of IDS probabilities"):
        simulate_ids_channel(
            sequence="ACGT",
            insertion_probability=0.4,
            deletion_probability=0.4,
            substitution_probability=0.3,
            rng=random.Random(42),
        )


def test_insertion_probability_one_is_rejected_to_guarantee_termination():
    with pytest.raises(ValueError, match="must be less than 1"):
        simulate_ids_channel(
            sequence="ACGT",
            insertion_probability=1.0,
            deletion_probability=0.0,
            substitution_probability=0.0,
            rng=random.Random(42),
        )


def test_cluster_generation_returns_requested_number_of_independent_traces():
    cluster = generate_trace_cluster(
        sequence="ACGTACGT",
        cluster_size=5,
        insertion_probability=0.1,
        deletion_probability=0.1,
        substitution_probability=0.1,
        rng=random.Random(42),
    )

    assert len(cluster) == 5
    assert all(set(trace) <= set(DNA_ALPHABET) for trace in cluster)
    assert len(set(cluster)) > 1


@pytest.mark.parametrize("cluster_size", [0, -1])
def test_cluster_size_must_be_positive(cluster_size):
    with pytest.raises(ValueError, match="at least 1"):
        generate_trace_cluster(
            sequence="ACGT",
            cluster_size=cluster_size,
            insertion_probability=0.1,
            deletion_probability=0.1,
            substitution_probability=0.1,
            rng=random.Random(42),
        )
