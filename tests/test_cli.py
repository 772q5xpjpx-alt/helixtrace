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
