"""Benchmark end-to-end recovery of small files from synthetic noisy DNA reads.

The benchmark is intentionally narrow and reproducible: it uses synthetic
binary payloads, the constrained file encoder, pre-grouped and pre-ordered read
clusters, and the deterministic consensus decoder.  It describes performance
under those controlled assumptions; it is not evidence from wet-lab reads.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from statistics import mean
from typing import Any

from dna_trace_reconstruction.file_pipeline import run_file_recovery

DEFAULT_MASTER_SEED = 20260720
DEFAULT_SAMPLES_PER_CELL = 12
DEFAULT_PAYLOAD_BYTES = 16
DEFAULT_FRAGMENT_BASES = 64
DEFAULT_CLUSTER_SIZES = (7, 11)
DEFAULT_EVENT_PROBABILITIES = (0.01, 0.02)
DEFAULT_DECODER = "consensus"
DEFAULT_FILENAME = "benchmark.bin"
DEFAULT_MEDIA_TYPE = "application/octet-stream"

CSV_FIELDS = (
    "cluster_size",
    "event_probability",
    "sample_index",
    "payload_seed",
    "channel_seed",
    "payload_sha256",
    "payload_bytes",
    "encoded_nucleotides",
    "fragment_count",
    "full_file_sha_success",
    "exact_fragment_count",
    "exact_fragment_percent",
    "mean_fragment_normalized_edit_distance",
    "runtime_seconds",
    "recovery_error",
)


def derive_seed(master_seed: int, *, purpose: str, condition: str, sample_index: int) -> int:
    """Derive a stable, domain-separated 64-bit seed.

    Payload and channel randomness use different ``purpose`` labels, so neither
    stream consumes state from the other.  Including the condition makes every
    sample reproducible even if conditions are reordered or filtered.
    """
    material = f"{master_seed}\x1f{purpose}\x1f{condition}\x1f{sample_index}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _random_payload(size_bytes: int, seed: int) -> bytes:
    rng = random.Random(seed)
    return bytes(rng.randrange(256) for _ in range(size_bytes))


def _condition_label(cluster_size: int, event_probability: float) -> str:
    return f"cluster={cluster_size};p={event_probability:.12g}"


def _validate_positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be an integer of at least 1")


def _validated_conditions(
    cluster_sizes: Iterable[int], event_probabilities: Iterable[float]
) -> tuple[tuple[int, ...], tuple[float, ...]]:
    clusters = tuple(cluster_sizes)
    probabilities = tuple(float(value) for value in event_probabilities)
    if not clusters:
        raise ValueError("cluster_sizes cannot be empty")
    if not probabilities:
        raise ValueError("event_probabilities cannot be empty")
    for cluster_size in clusters:
        _validate_positive_integer("each cluster size", cluster_size)
    for probability in probabilities:
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0 / 3.0:
            raise ValueError(
                "each event probability must be finite and between 0 and 1/3 because "
                "it is applied independently as the categorical insertion, deletion, "
                "and substitution value"
            )
    return clusters, probabilities


def run_file_benchmark(
    *,
    samples_per_cell: int = DEFAULT_SAMPLES_PER_CELL,
    payload_bytes: int = DEFAULT_PAYLOAD_BYTES,
    fragment_bases: int = DEFAULT_FRAGMENT_BASES,
    cluster_sizes: Iterable[int] = DEFAULT_CLUSTER_SIZES,
    event_probabilities: Iterable[float] = DEFAULT_EVENT_PROBABILITIES,
    master_seed: int = DEFAULT_MASTER_SEED,
    decoder: str = DEFAULT_DECODER,
    filename: str | None = DEFAULT_FILENAME,
    media_type: str | None = DEFAULT_MEDIA_TYPE,
) -> tuple[list[dict[str, Any]], float]:
    """Run every file-recovery condition and return per-file rows and wall time."""
    _validate_positive_integer("samples_per_cell", samples_per_cell)
    _validate_positive_integer("payload_bytes", payload_bytes)
    _validate_positive_integer("fragment_bases", fragment_bases)
    if fragment_bases % 8:
        raise ValueError("fragment_bases must be divisible by 8")
    if isinstance(master_seed, bool) or not isinstance(master_seed, int) or master_seed < 0:
        raise ValueError("master_seed must be a non-negative integer")
    clusters, probabilities = _validated_conditions(cluster_sizes, event_probabilities)

    rows: list[dict[str, Any]] = []
    benchmark_started = time.perf_counter()
    for cluster_size in clusters:
        for event_probability in probabilities:
            condition = _condition_label(cluster_size, event_probability)
            for sample_index in range(samples_per_cell):
                payload_seed = derive_seed(
                    master_seed,
                    purpose="payload",
                    condition=condition,
                    sample_index=sample_index,
                )
                channel_seed = derive_seed(
                    master_seed,
                    purpose="channel",
                    condition=condition,
                    sample_index=sample_index,
                )
                payload = _random_payload(payload_bytes, payload_seed)

                sample_started = time.perf_counter()
                result = run_file_recovery(
                    payload,
                    filename=filename,
                    media_type=media_type,
                    fragment_bases=fragment_bases,
                    cluster_size=cluster_size,
                    insertion_probability=event_probability,
                    deletion_probability=event_probability,
                    substitution_probability=event_probability,
                    seed=channel_seed,
                    decoder=decoder,
                )
                runtime_seconds = time.perf_counter() - sample_started

                fragment_count = result.fragment_count
                exact_fragment_count = result.exact_fragment_count
                mean_fragment_ned = mean(
                    fragment.normalized_edit_distance for fragment in result.fragments
                )
                rows.append(
                    {
                        "cluster_size": cluster_size,
                        "event_probability": event_probability,
                        "sample_index": sample_index,
                        "payload_seed": payload_seed,
                        "channel_seed": channel_seed,
                        "payload_sha256": result.original_sha256,
                        "payload_bytes": result.original_size_bytes,
                        "encoded_nucleotides": result.encoded_nucleotides,
                        "fragment_count": fragment_count,
                        "full_file_sha_success": int(result.checksum_verified),
                        "exact_fragment_count": exact_fragment_count,
                        "exact_fragment_percent": 100 * exact_fragment_count / fragment_count,
                        "mean_fragment_normalized_edit_distance": mean_fragment_ned,
                        "runtime_seconds": runtime_seconds,
                        "recovery_error": result.error or "",
                    }
                )

    return rows, time.perf_counter() - benchmark_started


def _aggregate_rows(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot aggregate an empty benchmark")
    total_fragments = sum(int(row["fragment_count"]) for row in rows)
    exact_fragments = sum(int(row["exact_fragment_count"]) for row in rows)
    weighted_ned = sum(
        float(row["mean_fragment_normalized_edit_distance"]) * int(row["fragment_count"])
        for row in rows
    )
    sha_successes = sum(int(row["full_file_sha_success"]) for row in rows)
    runtimes = [float(row["runtime_seconds"]) for row in rows]
    return {
        "files": len(rows),
        "full_file_sha_successes": sha_successes,
        "full_file_sha_success_percent": 100 * sha_successes / len(rows),
        "exact_fragments": exact_fragments,
        "total_fragments": total_fragments,
        "exact_fragment_percent": 100 * exact_fragments / total_fragments,
        "mean_fragment_normalized_edit_distance": weighted_ned / total_fragments,
        "mean_file_runtime_seconds": mean(runtimes),
        "total_file_runtime_seconds": sum(runtimes),
    }


def summarize_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate rows by cluster size and per-event IDS probability."""
    groups: dict[tuple[int, float], list[dict[str, Any]]] = {}
    for row in rows:
        key = (int(row["cluster_size"]), float(row["event_probability"]))
        groups.setdefault(key, []).append(row)

    summary: list[dict[str, Any]] = []
    for (cluster_size, event_probability), values in sorted(groups.items()):
        aggregate = _aggregate_rows(values)
        summary.append(
            {
                "cluster_size": cluster_size,
                "event_probability": event_probability,
                **aggregate,
            }
        )
    return summary


def build_report(
    rows: Sequence[dict[str, Any]],
    *,
    elapsed_seconds: float,
    samples_per_cell: int,
    payload_bytes: int,
    fragment_bases: int,
    cluster_sizes: Iterable[int],
    event_probabilities: Iterable[float],
    master_seed: int,
    decoder: str,
    filename: str | None,
    media_type: str | None,
) -> dict[str, Any]:
    """Build the self-describing JSON artifact for a completed run."""
    rows_list = list(rows)
    return {
        "benchmark": "HelixTrace end-to-end synthetic file recovery benchmark",
        "scope": (
            "Descriptive synthetic benchmark with read clusters grouped and fragment order "
            "provided out of band; no wet-lab data, clustering, or address recovery."
        ),
        "config": {
            "master_seed": master_seed,
            "samples_per_cell": samples_per_cell,
            "payload_bytes": payload_bytes,
            "encoding": "constrained-1bit-v1",
            "fragment_bases": fragment_bases,
            "cluster_sizes": list(cluster_sizes),
            "event_probabilities": list(event_probabilities),
            "decoder": decoder,
            "filename": filename,
            "media_type": media_type,
            "routing_metadata": "out-of-band-fragment-index",
            "event_probability_note": (
                "Insertion, deletion, and substitution each use the listed categorical "
                "per-event probability."
            ),
            "seed_note": (
                "Payload and channel seeds are deterministic SHA-256-derived, "
                "domain-separated streams for each condition and sample."
            ),
        },
        "elapsed_seconds": elapsed_seconds,
        "overall": _aggregate_rows(rows_list),
        "summary": summarize_rows(rows_list),
        "rows": rows_list,
    }


def write_artifacts(report: dict[str, Any], *, json_path: Path, csv_path: Path) -> None:
    """Write one auditable JSON report and its per-file CSV companion."""
    rows = report["rows"]
    if not rows:
        raise ValueError("report rows cannot be empty")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _print_summary(summary: Sequence[dict[str, Any]]) -> None:
    print(
        f"{'reads':>5} {'p/event':>7} {'files':>5} {'file SHA%':>9} "
        f"{'fragment%':>10} {'mean NED':>9} {'seconds':>8}"
    )
    for row in summary:
        print(
            f"{row['cluster_size']:>5} "
            f"{row['event_probability']:>7.2f} "
            f"{row['files']:>5} "
            f"{row['full_file_sha_success_percent']:>9.1f} "
            f"{row['exact_fragment_percent']:>10.1f} "
            f"{row['mean_fragment_normalized_edit_distance']:>9.5f} "
            f"{row['total_file_runtime_seconds']:>8.2f}"
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-per-cell", type=int, default=DEFAULT_SAMPLES_PER_CELL)
    parser.add_argument("--payload-bytes", type=int, default=DEFAULT_PAYLOAD_BYTES)
    parser.add_argument("--fragment-bases", type=int, default=DEFAULT_FRAGMENT_BASES)
    parser.add_argument("--cluster-sizes", type=int, nargs="+", default=list(DEFAULT_CLUSTER_SIZES))
    parser.add_argument(
        "--event-probabilities",
        type=float,
        nargs="+",
        default=list(DEFAULT_EVENT_PROBABILITIES),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_MASTER_SEED)
    parser.add_argument("--decoder", default=DEFAULT_DECODER)
    parser.add_argument("--filename", default=DEFAULT_FILENAME)
    parser.add_argument("--media-type", default=DEFAULT_MEDIA_TYPE)
    parser.add_argument(
        "--json-path", type=Path, default=Path("artifacts/file_recovery_benchmark.json")
    )
    parser.add_argument(
        "--csv-path", type=Path, default=Path("artifacts/file_recovery_benchmark.csv")
    )
    return parser.parse_args()


def main() -> None:
    arguments = _parse_args()
    try:
        rows, elapsed_seconds = run_file_benchmark(
            samples_per_cell=arguments.samples_per_cell,
            payload_bytes=arguments.payload_bytes,
            fragment_bases=arguments.fragment_bases,
            cluster_sizes=arguments.cluster_sizes,
            event_probabilities=arguments.event_probabilities,
            master_seed=arguments.seed,
            decoder=arguments.decoder,
            filename=arguments.filename,
            media_type=arguments.media_type,
        )
    except (TypeError, ValueError) as error:
        raise SystemExit(f"Invalid benchmark configuration: {error}") from error

    report = build_report(
        rows,
        elapsed_seconds=elapsed_seconds,
        samples_per_cell=arguments.samples_per_cell,
        payload_bytes=arguments.payload_bytes,
        fragment_bases=arguments.fragment_bases,
        cluster_sizes=arguments.cluster_sizes,
        event_probabilities=arguments.event_probabilities,
        master_seed=arguments.seed,
        decoder=arguments.decoder,
        filename=arguments.filename,
        media_type=arguments.media_type,
    )
    write_artifacts(report, json_path=arguments.json_path, csv_path=arguments.csv_path)
    _print_summary(report["summary"])
    overall_sha_percent = report["overall"]["full_file_sha_success_percent"]
    print(f"\nOverall full-file SHA success: {overall_sha_percent:.1f}%")
    print(f"Wrote {arguments.json_path.resolve()} and {arguments.csv_path.resolve()}")
    print(f"Wall time: {elapsed_seconds:.2f} seconds")


if __name__ == "__main__":
    main()
