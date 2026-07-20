import itertools

import pytest

import dna_trace_reconstruction.reconstruction as reconstruction
from dna_trace_reconstruction.metrics import levenshtein_distance
from dna_trace_reconstruction.reconstruction import (
    AlignmentCalls,
    consensus_round,
    global_align,
    parse_alignment,
    reconstruct_consensus,
    trace_medoid,
)


def test_global_alignment_preserves_inputs_and_realizes_edit_distance():
    aligned_reference, aligned_trace = global_align("ACGT", "ATCGT")

    assert aligned_reference.replace("-", "") == "ACGT"
    assert aligned_trace.replace("-", "") == "ATCGT"
    assert len(aligned_reference) == len(aligned_trace)
    assert sum(
        reference_base != trace_base
        for reference_base, trace_base in zip(aligned_reference, aligned_trace, strict=True)
    ) == levenshtein_distance("ACGT", "ATCGT")


def test_global_alignment_handles_empty_sequences():
    assert global_align("", "AC") == ("--", "AC")
    assert global_align("AC", "") == ("AC", "--")


def test_parse_alignment_separates_boundary_insertions_and_base_calls():
    calls = parse_alignment("A-CG-T", "AT-GGT")

    assert calls == AlignmentCalls(
        insertions=("", "T", "", "G", ""),
        bases=("A", "-", "G", "T"),
    )


def test_trace_medoid_minimizes_cluster_distance():
    assert trace_medoid(["ACGT", "ACGA", "TCGA"]) == "ACGA"


def test_trace_medoid_tie_break_is_order_independent():
    assert {
        trace_medoid(permutation) for permutation in itertools.permutations(["T", "A", "C"])
    } == {"A"}


def test_consensus_round_recovers_sequence_not_present_in_cluster():
    traces = ["ACGA", "TCGT", "AGGT"]

    assert trace_medoid(traces) == "ACGA"
    assert consensus_round(trace_medoid(traces), traces) == "ACGT"


def test_consensus_round_accepts_majority_insertion():
    assert consensus_round("ACGT", ["ATCGT", "ATCGT", "ACGT"]) == "ATCGT"


def test_boundary_insertion_tie_conservatively_prefers_no_insertion():
    assert consensus_round("ACGT", ["ATCGT", "ACGT"]) == "ACGT"


def test_consensus_round_accepts_majority_deletion():
    assert consensus_round("ACGT", ["AGT", "AGT", "ACGT"]) == "AGT"


def test_reconstruction_is_independent_of_trace_order():
    traces = ["ACGA", "TCGT", "AGGT"]

    outputs = {reconstruct_consensus(permutation) for permutation in itertools.permutations(traces)}

    assert outputs == {"ACGT"}


def test_reconstruction_resolves_a_cycle_by_cluster_evidence(monkeypatch):
    def toggle(reference, traces):
        return "C" if reference == "A" else "A"

    monkeypatch.setattr(reconstruction, "consensus_round", toggle)

    assert reconstruct_consensus(["A"], max_rounds=5) == "A"


def test_empty_trace_cluster_is_rejected():
    with pytest.raises(ValueError, match="at least one"):
        reconstruct_consensus([])


def test_one_string_is_not_accepted_as_a_trace_cluster():
    with pytest.raises(TypeError, match="not one string"):
        trace_medoid("ACGT")


@pytest.mark.parametrize("max_rounds", [0, -1])
def test_max_rounds_must_be_positive(max_rounds):
    with pytest.raises(ValueError, match="at least 1"):
        reconstruct_consensus(["ACGT"], max_rounds=max_rounds)


def test_invalid_dna_and_invalid_alignments_are_rejected():
    with pytest.raises(ValueError, match="invalid DNA bases"):
        global_align("ACNT", "ACGT")
    with pytest.raises(ValueError, match="equal length"):
        parse_alignment("AC", "A")
    with pytest.raises(ValueError, match="two gaps"):
        parse_alignment("A-", "A-")
