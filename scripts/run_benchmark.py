"""Run the deterministic HelixTrace synthetic benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import random
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from dna_trace_reconstruction.constraints import summarize_biological_constraints
from dna_trace_reconstruction.pipeline import CandidateEvaluation, run_experiment
from dna_trace_reconstruction.source_design import generate_constrained_source

METHOD_FIELDS = ("medoid", "consensus", "unconstrained", "constrained")


def _generate_gc_negative_control(length: int, rng: random.Random) -> str:
    """Generate a strand that intentionally violates the assumed GC prior."""
    for _ in range(10_000):
        sequence = "".join(rng.choices("ACGT", weights=(0.35, 0.15, 0.15, 0.35), k=length))
        summary = summarize_biological_constraints(sequence)
        if summary.gc_fraction < 0.40 and summary.max_homopolymer_run <= 3:
            return sequence
    raise RuntimeError("Could not generate a GC negative-control source")


def _candidate_row(
    *,
    profile: str,
    cluster_size: int,
    event_probability: float,
    sample_index: int,
    source_seed: int,
    channel_seed: int,
    method: str,
    candidate: CandidateEvaluation,
) -> dict[str, Any]:
    return {
        "source_profile": profile,
        "cluster_size": cluster_size,
        "event_probability": event_probability,
        "sample_index": sample_index,
        "source_seed": source_seed,
        "channel_seed": channel_seed,
        "method": method,
        "edit_distance": candidate.edit_distance,
        "normalized_edit_distance": candidate.normalized_edit_distance,
        "exact_recovery": int(candidate.exact_recovery),
        "biologically_valid": int(candidate.biologically_valid),
        "gc_fraction": candidate.gc_fraction,
        "max_homopolymer_run": candidate.max_homopolymer_run,
        "evidence_cost": candidate.evidence_cost,
    }


def run_benchmark(
    *,
    samples_per_cell: int,
    sequence_length: int,
    master_seed: int,
    include_negative_control: bool,
) -> tuple[list[dict[str, Any]], float]:
    """Run all benchmark cells and return long-form rows and wall time."""
    master_rng = random.Random(master_seed)
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    conditions: list[tuple[str, int, float]] = [
        ("constraint-compliant", cluster_size, error_probability)
        for cluster_size in (3, 5, 10)
        for error_probability in (0.03, 0.06)
    ]
    if include_negative_control:
        conditions.append(("gc-negative-control", 5, 0.03))

    for profile, cluster_size, event_probability in conditions:
        for sample_index in range(samples_per_cell):
            source_seed = master_rng.randrange(2**32)
            channel_seed = master_rng.randrange(2**32)
            source_rng = random.Random(source_seed)
            if profile == "constraint-compliant":
                source = generate_constrained_source(sequence_length, source_rng)
            else:
                source = _generate_gc_negative_control(sequence_length, source_rng)

            result = run_experiment(
                source,
                cluster_size=cluster_size,
                insertion_probability=event_probability,
                deletion_probability=event_probability,
                substitution_probability=event_probability,
                seed=channel_seed,
                lambda_gc=1.0,
                lambda_homopolymer=1.0,
                local_search_steps=3,
            )
            for method in METHOD_FIELDS:
                rows.append(
                    _candidate_row(
                        profile=profile,
                        cluster_size=cluster_size,
                        event_probability=event_probability,
                        sample_index=sample_index,
                        source_seed=source_seed,
                        channel_seed=channel_seed,
                        method=method,
                        candidate=getattr(result, method),
                    )
                )

    return rows, time.perf_counter() - started


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate benchmark rows by profile, condition, and method."""
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            row["source_profile"],
            row["cluster_size"],
            row["event_probability"],
            row["method"],
        )
        groups[key].append(row)

    summary: list[dict[str, Any]] = []
    for key in sorted(groups):
        profile, cluster_size, event_probability, method = key
        values = groups[key]
        summary.append(
            {
                "source_profile": profile,
                "cluster_size": cluster_size,
                "event_probability": event_probability,
                "method": method,
                "experiments": len(values),
                "exact_recovery_percent": 100 * mean(row["exact_recovery"] for row in values),
                "mean_edit_distance": mean(row["edit_distance"] for row in values),
                "mean_normalized_edit_distance": mean(
                    row["normalized_edit_distance"] for row in values
                ),
                "biologically_valid_percent": 100
                * mean(row["biologically_valid"] for row in values),
            }
        )
    return summary


def summarize_overall(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate all conditions within each source profile and method."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["source_profile"], row["method"])].append(row)

    overall: list[dict[str, Any]] = []
    for (profile, method), values in sorted(groups.items()):
        overall.append(
            {
                "source_profile": profile,
                "method": method,
                "experiments": len(values),
                "exact_recovery_percent": 100 * mean(row["exact_recovery"] for row in values),
                "mean_edit_distance": mean(row["edit_distance"] for row in values),
                "mean_normalized_edit_distance": mean(
                    row["normalized_edit_distance"] for row in values
                ),
                "biologically_valid_percent": 100
                * mean(row["biologically_valid"] for row in values),
            }
        )
    return overall


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(summary: list[dict[str, Any]]) -> None:
    print(
        f"{'profile':<22} {'n':>2} {'p/event':>7} {'method':<12} "
        f"{'exact%':>7} {'mean NED':>9} {'valid%':>7}"
    )
    for row in summary:
        print(
            f"{row['source_profile']:<22} "
            f"{row['cluster_size']:>2} "
            f"{row['event_probability']:>7.2f} "
            f"{row['method']:<12} "
            f"{row['exact_recovery_percent']:>7.1f} "
            f"{row['mean_normalized_edit_distance']:>9.4f} "
            f"{row['biologically_valid_percent']:>7.1f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-cell", type=int, default=12)
    parser.add_argument("--sequence-length", type=int, default=60)
    parser.add_argument("--seed", type=int, default=20260720)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--skip-negative-control", action="store_true")
    arguments = parser.parse_args()

    if arguments.samples_per_cell < 1:
        parser.error("--samples-per-cell must be at least 1")

    rows, elapsed_seconds = run_benchmark(
        samples_per_cell=arguments.samples_per_cell,
        sequence_length=arguments.sequence_length,
        master_seed=arguments.seed,
        include_negative_control=not arguments.skip_negative_control,
    )
    summary = summarize_rows(rows)
    overall = summarize_overall(rows)

    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(arguments.output_dir / "benchmark_rows.csv", rows)
    _write_csv(arguments.output_dir / "benchmark_summary.csv", summary)
    _write_csv(arguments.output_dir / "benchmark_overall.csv", overall)
    report = {
        "benchmark": "HelixTrace controlled synthetic benchmark",
        "master_seed": arguments.seed,
        "sequence_length": arguments.sequence_length,
        "samples_per_cell": arguments.samples_per_cell,
        "constraint_compliant_source_rules": {
            "minimum_gc_fraction": 0.45,
            "maximum_gc_fraction": 0.55,
            "maximum_homopolymer_run": 3,
        },
        "cluster_sizes": [3, 5, 10],
        "event_probabilities": [0.03, 0.06],
        "local_search_steps": 3,
        "lambda_gc": 1.0,
        "lambda_homopolymer": 1.0,
        "event_probability_note": (
            "Insertion, deletion, and substitution each use this categorical per-event value."
        ),
        "elapsed_seconds": elapsed_seconds,
        "overall": overall,
        "summary": summary,
    }
    (arguments.output_dir / "benchmark_summary.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    _print_summary(summary)
    print(f"\nWrote benchmark artifacts to {arguments.output_dir.resolve()}")
    print(f"Wall time: {elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()
