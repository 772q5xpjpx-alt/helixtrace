import json
import math
from pathlib import Path

import pytest

from dna_trace_reconstruction.learned_reranker import (
    DEFAULT_MODEL,
    FEATURE_NAMES,
    METHOD_NAMES,
    LinearRerankerModel,
    extract_candidate_features,
    rerank_candidates,
)
from dna_trace_reconstruction.pipeline import run_experiment


def _candidate_mapping(result):
    return {name: getattr(result, name).sequence for name in METHOD_NAMES}


def test_default_model_is_versioned_and_has_a_complete_parameter_vector():
    assert DEFAULT_MODEL.version == "helixtrace-linear-reranker-v1"
    assert DEFAULT_MODEL.training_seed == 20260720
    assert DEFAULT_MODEL.training_experiments == 80
    assert DEFAULT_MODEL.ridge_alpha == 10.0
    assert DEFAULT_MODEL.feature_names == FEATURE_NAMES
    assert len(DEFAULT_MODEL.weights) == len(FEATURE_NAMES) == 24


def test_committed_provenance_artifact_matches_default_model():
    artifact_path = (
        Path(__file__).parents[1] / "src/dna_trace_reconstruction/data/learned_reranker_v1.json"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert artifact["model_version"] == DEFAULT_MODEL.version
    assert artifact["training_split"]["master_seed"] == DEFAULT_MODEL.training_seed
    assert artifact["training_split"]["experiments"] == DEFAULT_MODEL.training_experiments
    assert artifact["source_available_at_inference"] is False
    assert artifact["held_out_metrics"]["learned"]["mean_edit_distance"] == pytest.approx(
        1.9916666666666667
    )


def test_feature_extraction_is_source_free_and_finite():
    result = run_experiment(
        "ACGTACGTACGTACGT",
        cluster_size=5,
        insertion_probability=0.06,
        deletion_probability=0.06,
        substitution_probability=0.06,
        seed=42,
        local_search_steps=3,
    )

    features = extract_candidate_features(result.traces, _candidate_mapping(result))

    assert tuple(features) == METHOD_NAMES
    assert all(len(vector) == len(FEATURE_NAMES) for vector in features.values())
    assert all(math.isfinite(value) for vector in features.values() for value in vector)
    evidence_above_best_index = FEATURE_NAMES.index("normalized_evidence_cost_above_best")
    assert min(vector[evidence_above_best_index] for vector in features.values()) == 0.0


def test_reranker_is_deterministic_and_selects_an_existing_candidate():
    result = run_experiment(
        "ACGTACGTACGTACGTACGT",
        cluster_size=5,
        insertion_probability=0.06,
        deletion_probability=0.06,
        substitution_probability=0.06,
        seed=42,
        local_search_steps=3,
    )
    candidates = _candidate_mapping(result)

    first = rerank_candidates(result.traces, candidates)
    second = rerank_candidates(result.traces, candidates)

    assert first == second
    assert first.selected_name == "unconstrained"
    assert first.selected_sequence == candidates[first.selected_name]
    assert tuple(score.name for score in first.scores) == METHOD_NAMES
    assert first.model_version == DEFAULT_MODEL.version


def test_zero_noise_selection_cannot_damage_identical_candidates():
    source = "ACGTACGT"
    candidates = {name: source for name in METHOD_NAMES}

    result = rerank_candidates([source, source, source], candidates)

    assert result.selected_sequence == source


def test_model_injection_and_tie_break_are_deterministic():
    zero_model = LinearRerankerModel(
        version="zero-test-model",
        feature_names=FEATURE_NAMES,
        feature_means=(0.0,) * len(FEATURE_NAMES),
        feature_scales=(1.0,) * len(FEATURE_NAMES),
        intercept=0.0,
        weights=(0.0,) * len(FEATURE_NAMES),
        training_seed=0,
        training_experiments=1,
        ridge_alpha=1.0,
    )
    candidates = {
        "medoid": "ACGA",
        "consensus": "ACGT",
        "unconstrained": "ACGT",
        "constrained": "ACGT",
    }

    result = rerank_candidates(["ACGT", "ACGA"], candidates, model=zero_model)

    assert result.selected_name == "medoid"
    assert result.model_version == "zero-test-model"


def test_reranker_rejects_incomplete_candidate_sets_and_invalid_dna():
    with pytest.raises(ValueError, match="require exactly"):
        rerank_candidates(["ACGT"], {"consensus": "ACGT"})

    candidates = {name: "ACGT" for name in METHOD_NAMES}
    candidates["medoid"] = "ACNT"
    with pytest.raises(ValueError, match="invalid DNA bases"):
        rerank_candidates(["ACGT"], candidates)
