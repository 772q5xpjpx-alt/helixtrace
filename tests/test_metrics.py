import pytest

from dna_trace_reconstruction.metrics import (
    levenshtein_distance,
    normalized_edit_distance,
)


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ("", "", 0),
        ("ACGT", "ACGT", 0),
        ("", "ACGT", 4),
        ("ACGT", "", 4),
        ("ACGT", "AGGT", 1),
        ("ACGT", "ACGTT", 1),
        ("ACGTT", "ACGT", 1),
        ("kitten", "sitting", 3),
    ],
)
def test_levenshtein_distance(first, second, expected):
    assert levenshtein_distance(first, second) == expected
    assert levenshtein_distance(second, first) == expected


def test_normalized_edit_distance_uses_longer_length():
    assert normalized_edit_distance("ACGT", "ACGTT") == pytest.approx(0.2)


def test_normalized_edit_distance_for_empty_sequences():
    assert normalized_edit_distance("", "") == 0.0
    assert normalized_edit_distance("", "ACGT") == 1.0


def test_metrics_require_strings():
    with pytest.raises(TypeError, match="first must be a string"):
        levenshtein_distance(None, "ACGT")

    with pytest.raises(TypeError, match="second must be a string"):
        normalized_edit_distance("ACGT", ["A", "C", "G", "T"])
