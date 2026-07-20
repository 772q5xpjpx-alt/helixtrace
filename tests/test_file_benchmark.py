import csv
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "run_file_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_file_benchmark", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
BENCHMARK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCHMARK)

build_report = BENCHMARK.build_report
derive_seed = BENCHMARK.derive_seed
run_file_benchmark = BENCHMARK.run_file_benchmark
summarize_rows = BENCHMARK.summarize_rows
write_artifacts = BENCHMARK.write_artifacts


def test_seed_derivation_is_reproducible_and_domain_separated():
    arguments = {
        "master_seed": 20260720,
        "condition": "cluster=7;p=0.01",
        "sample_index": 0,
    }

    payload_seed = derive_seed(purpose="payload", **arguments)

    assert payload_seed == derive_seed(purpose="payload", **arguments)
    assert payload_seed != derive_seed(purpose="channel", **arguments)
    assert payload_seed != derive_seed(purpose="payload", **{**arguments, "sample_index": 1})


def test_zero_noise_file_benchmark_is_exact_and_reproducible():
    kwargs = {
        "samples_per_cell": 2,
        "payload_bytes": 4,
        "fragment_bases": 64,
        "cluster_sizes": (1,),
        "event_probabilities": (0.0,),
        "master_seed": 99,
        "decoder": "consensus",
        "filename": "smoke.bin",
        "media_type": "application/octet-stream",
    }

    first, _ = run_file_benchmark(**kwargs)
    second, _ = run_file_benchmark(**kwargs)

    stable_fields = [key for key in first[0] if key != "runtime_seconds"]
    assert [{key: row[key] for key in stable_fields} for row in first] == [
        {key: row[key] for key in stable_fields} for row in second
    ]
    assert all(row["full_file_sha_success"] == 1 for row in first)
    assert all(row["exact_fragment_count"] == row["fragment_count"] for row in first)
    assert all(row["mean_fragment_normalized_edit_distance"] == 0.0 for row in first)
    assert all(row["runtime_seconds"] >= 0.0 for row in first)

    summary = summarize_rows(first)
    assert summary[0]["full_file_sha_success_percent"] == 100.0
    assert summary[0]["exact_fragment_percent"] == 100.0
    assert summary[0]["mean_fragment_normalized_edit_distance"] == 0.0


def test_report_and_artifacts_preserve_auditable_rows(tmp_path):
    rows, elapsed = run_file_benchmark(
        samples_per_cell=1,
        payload_bytes=2,
        fragment_bases=64,
        cluster_sizes=(1,),
        event_probabilities=(0.0,),
        master_seed=7,
    )
    report = build_report(
        rows,
        elapsed_seconds=elapsed,
        samples_per_cell=1,
        payload_bytes=2,
        fragment_bases=64,
        cluster_sizes=(1,),
        event_probabilities=(0.0,),
        master_seed=7,
        decoder="consensus",
        filename="benchmark.bin",
        media_type="application/octet-stream",
    )
    json_path = tmp_path / "nested" / "benchmark.json"
    csv_path = tmp_path / "nested" / "benchmark.csv"

    write_artifacts(report, json_path=json_path, csv_path=csv_path)

    loaded_report = json.loads(json_path.read_text(encoding="utf-8"))
    with csv_path.open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert loaded_report["config"]["routing_metadata"] == "out-of-band-fragment-index"
    assert "no wet-lab data" in loaded_report["scope"]
    assert loaded_report["overall"]["files"] == 1
    assert len(loaded_report["rows"]) == len(csv_rows) == 1
    assert csv_rows[0]["payload_sha256"] == rows[0]["payload_sha256"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"samples_per_cell": 0}, "samples_per_cell"),
        ({"payload_bytes": 0}, "payload_bytes"),
        ({"fragment_bases": 63}, "divisible by 8"),
        ({"cluster_sizes": ()}, "cluster_sizes"),
        ({"event_probabilities": ()}, "event_probabilities"),
        ({"event_probabilities": (0.34,)}, "event probability"),
        ({"master_seed": -1}, "master_seed"),
    ],
)
def test_file_benchmark_rejects_invalid_configuration(kwargs, message):
    with pytest.raises(ValueError, match=message):
        run_file_benchmark(**kwargs)
