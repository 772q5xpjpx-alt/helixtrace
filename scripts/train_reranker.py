"""Train and evaluate HelixTrace's dependency-free linear candidate reranker.

This script is the reproducible provenance for the weights committed in
``learned_reranker.py``.  Training targets use known synthetic sources; the
held-out evaluation uses a disjoint master seed and inference receives only
noisy traces plus the four deterministic candidates.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict
from pathlib import Path
from statistics import fmean
from typing import Any

from dna_trace_reconstruction.learned_reranker import (
    DEFAULT_MODEL,
    FEATURE_NAMES,
    METHOD_NAMES,
    LinearRerankerModel,
    extract_candidate_features,
    rerank_candidates,
)
from dna_trace_reconstruction.pipeline import ExperimentResult, run_experiment
from dna_trace_reconstruction.source_design import generate_constrained_source

DEFAULT_TRAIN_SEED = 20260720
DEFAULT_TEST_SEED = 20260721
DEFAULT_TRAIN_EXPERIMENTS = 80
DEFAULT_TEST_EXPERIMENTS = 120
DEFAULT_RIDGE_ALPHA = 10.0

SEQUENCE_LENGTHS = (40, 60, 80)
CLUSTER_SIZES = (3, 5, 7, 10)
EVENT_PROBABILITIES = (0.02, 0.03, 0.04, 0.05, 0.06, 0.07)


def _candidate_mapping(result: ExperimentResult) -> dict[str, str]:
    return {name: getattr(result, name).sequence for name in METHOD_NAMES}


def generate_dataset(experiments: int, master_seed: int) -> list[ExperimentResult]:
    """Generate a deterministic synthetic dataset from one master seed."""
    if experiments < 1:
        raise ValueError("experiments must be at least 1")

    rng = random.Random(master_seed)
    dataset: list[ExperimentResult] = []
    for _ in range(experiments):
        sequence_length = rng.choice(SEQUENCE_LENGTHS)
        cluster_size = rng.choice(CLUSTER_SIZES)
        event_probability = rng.choice(EVENT_PROBABILITIES)
        source_seed = rng.randrange(2**32)
        source = generate_constrained_source(sequence_length, random.Random(source_seed))
        channel_seed = rng.randrange(2**32)
        dataset.append(
            run_experiment(
                source,
                cluster_size=cluster_size,
                insertion_probability=event_probability,
                deletion_probability=event_probability,
                substitution_probability=event_probability,
                seed=channel_seed,
                local_search_steps=3,
            )
        )
    return dataset


def _training_rows(
    dataset: list[ExperimentResult],
) -> tuple[list[tuple[float, ...]], list[float]]:
    features: list[tuple[float, ...]] = []
    targets: list[float] = []
    for result in dataset:
        vectors = extract_candidate_features(result.traces, _candidate_mapping(result))
        for name in METHOD_NAMES:
            features.append(vectors[name])
            targets.append(getattr(result, name).normalized_edit_distance)
    return features, targets


def _solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a dense system with deterministic partial-pivot elimination."""
    size = len(vector)
    augmented = [row[:] + [value] for row, value in zip(matrix, vector, strict=True)]

    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if math.isclose(augmented[pivot][column], 0.0, abs_tol=1e-15):
            raise ValueError("ridge system is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]

        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            augmented[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(augmented[row], augmented[column], strict=True)
            ]

    return [augmented[row][-1] for row in range(size)]


def fit_ridge_model(
    dataset: list[ExperimentResult],
    *,
    ridge_alpha: float,
    training_seed: int,
    version: str,
) -> LinearRerankerModel:
    """Fit standardized ridge regression without third-party ML libraries."""
    if not math.isfinite(ridge_alpha) or ridge_alpha <= 0.0:
        raise ValueError("ridge_alpha must be finite and positive")

    feature_rows, targets = _training_rows(dataset)
    feature_count = len(FEATURE_NAMES)
    means = tuple(fmean(row[column] for row in feature_rows) for column in range(feature_count))
    scales = tuple(
        math.sqrt(fmean((row[column] - means[column]) ** 2 for row in feature_rows)) or 1.0
        for column in range(feature_count)
    )
    design = [
        [1.0] + [(row[column] - means[column]) / scales[column] for column in range(feature_count)]
        for row in feature_rows
    ]

    parameter_count = feature_count + 1
    gram = [[0.0] * parameter_count for _ in range(parameter_count)]
    target_product = [0.0] * parameter_count
    for row, target in zip(design, targets, strict=True):
        for first_index, first_value in enumerate(row):
            target_product[first_index] += first_value * target
            for second_index, second_value in enumerate(row):
                gram[first_index][second_index] += first_value * second_value
    for index in range(1, parameter_count):
        gram[index][index] += ridge_alpha

    parameters = _solve_linear_system(gram, target_product)
    return LinearRerankerModel(
        version=version,
        feature_names=FEATURE_NAMES,
        feature_means=means,
        feature_scales=scales,
        intercept=parameters[0],
        weights=tuple(parameters[1:]),
        training_seed=training_seed,
        training_experiments=len(dataset),
        ridge_alpha=ridge_alpha,
    )


def evaluate_model(dataset: list[ExperimentResult], model: LinearRerankerModel) -> dict[str, Any]:
    """Compare learned selection with each fixed candidate and a candidate oracle."""
    totals = {
        name: {"edit_distance": 0.0, "normalized_edit_distance": 0.0, "exact": 0}
        for name in (*METHOD_NAMES, "learned", "candidate_oracle")
    }
    selection_counts = {name: 0 for name in METHOD_NAMES}

    for result in dataset:
        candidates = _candidate_mapping(result)
        learned = rerank_candidates(result.traces, candidates, model=model)
        selection_counts[learned.selected_name] += 1
        learned_evaluation = getattr(result, learned.selected_name)
        oracle_name = min(
            METHOD_NAMES,
            key=lambda name: (
                getattr(result, name).normalized_edit_distance,
                METHOD_NAMES.index(name),
            ),
        )

        evaluations = {name: getattr(result, name) for name in METHOD_NAMES}
        evaluations["learned"] = learned_evaluation
        evaluations["candidate_oracle"] = getattr(result, oracle_name)
        for name, evaluation in evaluations.items():
            totals[name]["edit_distance"] += evaluation.edit_distance
            totals[name]["normalized_edit_distance"] += evaluation.normalized_edit_distance
            totals[name]["exact"] += int(evaluation.exact_recovery)

    count = len(dataset)
    metrics = {
        name: {
            "mean_edit_distance": values["edit_distance"] / count,
            "mean_normalized_edit_distance": values["normalized_edit_distance"] / count,
            "exact_recovery_percent": 100.0 * values["exact"] / count,
        }
        for name, values in totals.items()
    }
    return {"experiments": count, "metrics": metrics, "learned_selection_counts": selection_counts}


def _maximum_default_parameter_difference(model: LinearRerankerModel) -> float:
    generated = (
        model.intercept,
        *model.feature_means,
        *model.feature_scales,
        *model.weights,
    )
    committed = (
        DEFAULT_MODEL.intercept,
        *DEFAULT_MODEL.feature_means,
        *DEFAULT_MODEL.feature_scales,
        *DEFAULT_MODEL.weights,
    )
    return max(abs(first - second) for first, second in zip(generated, committed, strict=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-experiments", type=int, default=DEFAULT_TRAIN_EXPERIMENTS)
    parser.add_argument("--test-experiments", type=int, default=DEFAULT_TEST_EXPERIMENTS)
    parser.add_argument("--train-seed", type=int, default=DEFAULT_TRAIN_SEED)
    parser.add_argument("--test-seed", type=int, default=DEFAULT_TEST_SEED)
    parser.add_argument("--ridge-alpha", type=float, default=DEFAULT_RIDGE_ALPHA)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    if arguments.train_experiments < 1 or arguments.test_experiments < 1:
        parser.error("experiment counts must be at least 1")
    if arguments.train_seed == arguments.test_seed:
        parser.error("training and held-out master seeds must differ")

    training_data = generate_dataset(arguments.train_experiments, arguments.train_seed)
    model = fit_ridge_model(
        training_data,
        ridge_alpha=arguments.ridge_alpha,
        training_seed=arguments.train_seed,
        version="helixtrace-linear-reranker-v1",
    )
    held_out_data = generate_dataset(arguments.test_experiments, arguments.test_seed)
    report = {
        "model": asdict(model),
        "training_split": {
            "experiments": arguments.train_experiments,
            "master_seed": arguments.train_seed,
        },
        "held_out_split": {
            "experiments": arguments.test_experiments,
            "master_seed": arguments.test_seed,
        },
        "synthetic_distribution": {
            "sequence_lengths": SEQUENCE_LENGTHS,
            "cluster_sizes": CLUSTER_SIZES,
            "insertion_deletion_substitution_probability_each": EVENT_PROBABILITIES,
            "source_constraints": "GC 45-55%; maximum homopolymer run 3",
            "local_search_steps": 3,
        },
        "training_metrics": evaluate_model(training_data, model),
        "held_out_metrics": evaluate_model(held_out_data, model),
        "committed_model_max_abs_parameter_difference": (
            _maximum_default_parameter_difference(model)
        ),
        "limitations": (
            "Controlled synthetic data only; candidate selection cannot repair an error that "
            "none of the four upstream candidates repaired. Held-out results from one split "
            "do not establish wet-lab generalization."
        ),
    }

    rendered = json.dumps(report, indent=2) + "\n"
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
