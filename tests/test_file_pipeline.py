import hashlib
import inspect

import pytest

from dna_trace_reconstruction.file_pipeline import (
    DEFAULT_ENCODING,
    SUPPORTED_DECODERS,
    reconstruct_fragment,
    run_file_recovery,
)


def test_zero_noise_binary_file_round_trip_is_exact():
    data = b"\x00\xff\x10HelixTrace\x00"

    result = run_file_recovery(
        data,
        filename="sample.bin",
        media_type="application/octet-stream",
        insertion_probability=0.0,
        deletion_probability=0.0,
        substitution_probability=0.0,
        decoder="medoid",
    )

    assert result.recovered_data == data
    assert result.recovered_filename == "sample.bin"
    assert result.recovered_media_type == "application/octet-stream"
    assert result.original_sha256 == hashlib.sha256(data).hexdigest()
    assert result.recovered_sha256 == result.original_sha256
    assert result.original_size_bytes == len(data)
    assert result.checksum_verified
    assert result.exact_file_recovery
    assert result.error is None
    assert result.fragment_count == len(result.fragments)
    assert result.exact_fragment_count == result.fragment_count
    assert result.config.encoding == DEFAULT_ENCODING
    assert result.config.routing_metadata == "out-of-band-fragment-index"
    assert all(fragment.edit_distance == 0 for fragment in result.fragments)


def test_default_noisy_recovery_is_reproducible_and_checksum_verified():
    data = b"DNA storage recovery"

    first = run_file_recovery(data, "message.txt", "text/plain", seed=42)
    second = run_file_recovery(data, "message.txt", "text/plain", seed=42)

    assert first == second
    assert any(
        trace != fragment.source for fragment in first.fragments for trace in fragment.traces
    )
    assert first.checksum_verified
    assert first.recovered_data == data
    assert first.error is None


def test_learned_decoder_uses_committed_model_without_ground_truth():
    result = run_file_recovery(
        b"ML",
        seed=42,
        decoder="learned",
        fragment_bases=40,
        local_search_steps=1,
    )

    assert result.checksum_verified
    assert result.recovered_data == b"ML"
    assert {fragment.model_version for fragment in result.fragments} == {
        "helixtrace-linear-reranker-v1"
    }
    assert all(
        fragment.selected_method in {"medoid", "consensus", "unconstrained", "constrained"}
        for fragment in result.fragments
    )
    assert all(fragment.candidate_variants is not None for fragment in result.fragments)


def test_high_noise_corruption_is_detected_without_crashing():
    result = run_file_recovery(
        b"integrity must fail closed",
        filename="proof.txt",
        cluster_size=1,
        insertion_probability=0.0,
        deletion_probability=0.45,
        substitution_probability=0.45,
        seed=7,
        decoder="medoid",
    )

    assert not result.checksum_verified
    assert not result.exact_file_recovery
    assert result.recovered_data is None
    assert result.recovered_sha256 is None
    assert result.error is not None
    assert "failed integrity or format validation" in result.error
    assert any(not fragment.exact for fragment in result.fragments)


@pytest.mark.parametrize("decoder", SUPPORTED_DECODERS)
def test_every_decoder_supports_an_exact_zero_noise_cluster(decoder):
    source = "ACGTCAGT" * 4
    traces = (source,) * 3

    assert reconstruct_fragment(traces, decoder=decoder) == source


def test_reconstruction_api_has_no_ground_truth_or_digest_input():
    parameters = inspect.signature(reconstruct_fragment).parameters

    assert "source" not in parameters
    assert "expected" not in parameters
    assert "sha256" not in parameters
    assert set(parameters) == {
        "traces",
        "decoder",
        "consensus_rounds",
        "local_search_steps",
        "lambda_gc",
        "lambda_homopolymer",
    }


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"fragment_bases": 63}, ValueError, "divisible by 8"),
        ({"cluster_size": 0}, ValueError, "cluster_size"),
        ({"seed": -1}, ValueError, "seed"),
        ({"decoder": "oracle"}, ValueError, "decoder"),
        ({"insertion_probability": float("nan")}, ValueError, "insertion_probability"),
        (
            {
                "insertion_probability": 0.4,
                "deletion_probability": 0.4,
                "substitution_probability": 0.4,
            },
            ValueError,
            "sum of IDS probabilities",
        ),
    ],
)
def test_file_recovery_validates_configuration(kwargs, error, message):
    with pytest.raises(error, match=message):
        run_file_recovery(b"x", **kwargs)


def test_file_recovery_rejects_non_bytes_input():
    with pytest.raises(TypeError, match="bytes-like"):
        run_file_recovery("not bytes")
