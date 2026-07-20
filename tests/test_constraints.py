import pytest

from dna_trace_reconstruction.constraints import (
    BiologicalSummary,
    constrained_local_search,
    evidence_cost,
    evidence_local_search,
    gc_count_excess,
    gc_fraction,
    homopolymer_excess,
    is_biologically_valid,
    max_homopolymer_run,
    reconstruction_objective,
    summarize_biological_constraints,
)


def test_gc_fraction_and_count_excess():
    assert gc_fraction("GGCCAAAA") == 0.5
    assert gc_count_excess("GGCCAAAA") == 0.0
    assert gc_count_excess("GGGGGGAA") == pytest.approx(1.6)
    assert gc_count_excess("GGAAAAAA") == pytest.approx(1.6)


def test_empty_sequence_metrics_are_defined_but_summary_is_invalid():
    summary = summarize_biological_constraints("")

    assert summary.gc_fraction == 0.0
    assert summary.max_homopolymer_run == 0
    assert summary.gc_excess == 0.0
    assert summary.homopolymer_excess == 0
    assert not summary.valid


@pytest.mark.parametrize(
    ("sequence", "expected"),
    [("", 0), ("ACGT", 1), ("AACCCG", 3), ("TTTTACCCCCC", 6)],
)
def test_max_homopolymer_run(sequence, expected):
    assert max_homopolymer_run(sequence) == expected


def test_homopolymer_excess_uses_longest_run():
    assert homopolymer_excess("AAACCC", maximum_homopolymer_run=3) == 0
    assert homopolymer_excess("AAAACCC", maximum_homopolymer_run=3) == 1


def test_biological_summary_reports_both_constraints():
    summary = summarize_biological_constraints("GGGGGGAAAA")

    assert summary == BiologicalSummary(
        gc_fraction=0.6,
        max_homopolymer_run=6,
        gc_excess=pytest.approx(0.5),
        homopolymer_excess=3,
        valid=False,
    )


def test_valid_sequence_passes_constraints():
    assert is_biologically_valid("ACGTACGT")


def test_custom_constraint_thresholds_are_supported():
    assert is_biologically_valid(
        "GGGAAA",
        minimum_gc_fraction=0.4,
        maximum_gc_fraction=0.6,
        maximum_homopolymer_run=3,
    )


def test_evidence_cost_is_mean_edit_distance():
    assert evidence_cost("ACGT", ["ACGT", "AGGT", "ACGTT"]) == pytest.approx(2 / 3)


def test_evidence_local_search_is_a_fair_optimization_control():
    initial = "AAAA"
    traces = ["CAAA", "CAAA", "AAAA"]

    result = evidence_local_search(initial, traces, max_iterations=1)

    assert result == "CAAA"
    assert evidence_cost(result, traces) < evidence_cost(initial, traces)


def test_evidence_and_constraint_search_can_make_different_choices():
    initial = "GGGGAACT"
    traces = [initial, initial, "AGGGAACT"]

    evidence_only = evidence_local_search(initial, traces, max_iterations=2)
    biology_aware = constrained_local_search(
        initial,
        traces,
        lambda_gc=2.0,
        lambda_homopolymer=2.0,
        max_iterations=2,
    )

    assert evidence_only == initial
    assert biology_aware != evidence_only
    assert summarize_biological_constraints(biology_aware).valid


def test_objective_adds_weighted_constraint_penalties():
    candidate = "GGGGAAAA"
    traces = [candidate]

    assert reconstruction_objective(
        candidate,
        traces,
        lambda_gc=2.0,
        lambda_homopolymer=3.0,
    ) == pytest.approx(3.0)


def test_zero_weight_local_search_returns_initial_sequence():
    initial = "GGGGAAAA"

    assert (
        constrained_local_search(
            initial,
            ["GCGCAAAA"],
            lambda_gc=0.0,
            lambda_homopolymer=0.0,
        )
        == initial
    )


def test_constrained_local_search_improves_constraints_without_changing_length():
    initial = "GGGGAACT"
    traces = [initial, initial, "AGGGAACT"]

    result = constrained_local_search(
        initial,
        traces,
        lambda_gc=2.0,
        lambda_homopolymer=2.0,
    )

    assert len(result) == len(initial)
    assert reconstruction_objective(
        result,
        traces,
        lambda_gc=2.0,
        lambda_homopolymer=2.0,
    ) < reconstruction_objective(
        initial,
        traces,
        lambda_gc=2.0,
        lambda_homopolymer=2.0,
    )
    assert summarize_biological_constraints(result).valid


def test_constrained_local_search_is_deterministic():
    arguments = {
        "initial_sequence": "GGGGAACT",
        "traces": ["GGGGAACT", "GGGGAACT", "AGGGAACT"],
        "lambda_gc": 2.0,
        "lambda_homopolymer": 2.0,
    }

    assert constrained_local_search(**arguments) == constrained_local_search(**arguments)


@pytest.mark.parametrize("sequence", ["ACNT", "acgt", "AC-G"])
def test_constraints_reject_invalid_dna(sequence):
    with pytest.raises(ValueError, match="Invalid DNA bases"):
        summarize_biological_constraints(sequence)


def test_evidence_cost_rejects_empty_trace_cluster():
    with pytest.raises(ValueError, match="at least one"):
        evidence_cost("ACGT", [])


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(-0.1, 0.5), (0.4, 1.1), (0.7, 0.3)],
)
def test_invalid_gc_bounds_are_rejected(minimum, maximum):
    with pytest.raises(ValueError):
        summarize_biological_constraints(
            "ACGT",
            minimum_gc_fraction=minimum,
            maximum_gc_fraction=maximum,
        )


def test_negative_constraint_weight_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        reconstruction_objective("ACGT", ["ACGT"], lambda_gc=-1.0)
