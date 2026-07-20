"""Sequence-level metrics for DNA trace reconstruction."""

from __future__ import annotations


def _validate_sequence(name: str, sequence: str) -> None:
    if not isinstance(sequence, str):
        raise TypeError(f"{name} must be a string")


def levenshtein_distance(first: str, second: str) -> int:
    """Return the minimum number of edits needed to transform one string.

    Insertions, deletions, and substitutions each have unit cost. The
    implementation stores only one dynamic-programming row, so its memory use
    is linear in the length of the shorter input.
    """
    _validate_sequence("first", first)
    _validate_sequence("second", second)

    if first == second:
        return 0

    # Keep ``second`` as the shorter sequence to minimize the DP row.
    if len(first) < len(second):
        first, second = second, first

    if not second:
        return len(first)

    previous_row = list(range(len(second) + 1))

    for first_index, first_symbol in enumerate(first, start=1):
        current_row = [first_index]
        for second_index, second_symbol in enumerate(second, start=1):
            insertion = current_row[second_index - 1] + 1
            deletion = previous_row[second_index] + 1
            substitution = previous_row[second_index - 1] + (first_symbol != second_symbol)
            current_row.append(min(insertion, deletion, substitution))
        previous_row = current_row

    return previous_row[-1]


def normalized_edit_distance(first: str, second: str) -> float:
    """Return Levenshtein distance divided by the longer input length.

    Two empty strings have normalized distance ``0.0``. Normalizing by the
    longer input keeps the result in the closed interval ``[0, 1]`` even when
    insertions and deletions change sequence length.
    """
    distance = levenshtein_distance(first, second)
    denominator = max(len(first), len(second))
    return distance / denominator if denominator else 0.0
