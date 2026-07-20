import pytest

from dna_trace_reconstruction.pipeline import (
    compact_experiment_payload,
    experiment_as_dict,
    run_experiment,
)


def test_zero_noise_pipeline_recovers_source_with_every_method():
    result = run_experiment(
        "ACGTACGT",
        cluster_size=3,
        insertion_probability=0,
        deletion_probability=0,
        substitution_probability=0,
        seed=11,
    )

    assert result.traces == ("ACGTACGT",) * 3
    for method in ("medoid", "consensus", "unconstrained", "constrained"):
        candidate = getattr(result, method)
        assert candidate.sequence == result.source
        assert candidate.exact_recovery
        assert candidate.edit_distance == 0


def test_pipeline_is_reproducible_for_a_fixed_seed():
    arguments = {
        "source": "ACGTACGTACGT",
        "cluster_size": 5,
        "insertion_probability": 0.08,
        "deletion_probability": 0.08,
        "substitution_probability": 0.08,
        "seed": 42,
    }

    assert run_experiment(**arguments) == run_experiment(**arguments)


def test_pipeline_result_is_json_compatible_and_bounded_for_gpt():
    result = run_experiment("ACGTACGT", cluster_size=2, seed=4)

    full_data = experiment_as_dict(result)
    compact_data = compact_experiment_payload(result)

    assert full_data["source"] == "ACGTACGT"
    assert set(compact_data["candidates"]) == {
        "medoid",
        "consensus",
        "unconstrained",
        "constrained",
    }
    assert compact_data["config"]["local_search_steps"] == 4
    assert "not a trained neural model" in compact_data["method_note"]


def test_pipeline_normalizes_lowercase_source():
    result = run_experiment(" acgt ", cluster_size=1, seed=1)
    assert result.source == "ACGT"


def test_pipeline_rejects_invalid_source():
    with pytest.raises(ValueError, match="Invalid DNA bases"):
        run_experiment("ACNT", cluster_size=3)
