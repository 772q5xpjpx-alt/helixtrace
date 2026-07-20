import sys

from dna_trace_reconstruction.cli import main


def test_cli_prints_reproducible_cluster(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dna-ids-demo",
            "--sequence",
            "ACGT",
            "--cluster-size",
            "2",
            "--insertion-probability",
            "0",
            "--deletion-probability",
            "0",
            "--substitution-probability",
            "0",
            "--seed",
            "42",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "Original sequence (4 nt): ACGT" in output
    assert "Trace  1 ( 4 nt): ACGT" in output
    assert "Trace  2 ( 4 nt): ACGT" in output
    assert "Reconstruction results" in output
    assert "Biology-aware decoding" in output


def test_cli_recovers_binary_file_and_writes_only_verified_output(monkeypatch, capsys, tmp_path):
    source = tmp_path / "tiny.bin"
    recovered = tmp_path / "recovered.bin"
    source.write_bytes(b"\x00HELIX\xff")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "helixtrace",
            "--input-file",
            str(source),
            "--output-file",
            str(recovered),
            "--cluster-size",
            "3",
            "--insertion-probability",
            "0",
            "--deletion-probability",
            "0",
            "--substitution-probability",
            "0",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert recovered.read_bytes() == source.read_bytes()
    assert "RECOVERY VERIFIED" in output
    assert "Wrote verified file" in output
