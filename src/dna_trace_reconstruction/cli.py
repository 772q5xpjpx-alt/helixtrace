"""Command-line experiment runner for HelixTrace."""

from __future__ import annotations

import argparse
import mimetypes
from pathlib import Path

from dna_trace_reconstruction.ai_analyst import analyze_experiment
from dna_trace_reconstruction.file_pipeline import SUPPORTED_DECODERS, run_file_recovery
from dna_trace_reconstruction.pipeline import run_experiment

DEFAULT_SEQUENCE = "ACGTACGTACGT"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Reconstruct a source from a synthetic cluster of noisy DNA traces."
    )
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--sequence",
        help=f"Source DNA sequence (default when no file is supplied: {DEFAULT_SEQUENCE})",
    )
    input_group.add_argument(
        "--input-file",
        type=Path,
        help="Recover a binary file through the synthetic DNA channel instead of one strand",
    )
    parser.add_argument(
        "--cluster-size",
        type=int,
        default=5,
        help="Number of traces to generate (default: %(default)s)",
    )
    parser.add_argument(
        "--insertion-probability",
        type=float,
        default=0.08,
        help="Insertion event probability (default: %(default)s)",
    )
    parser.add_argument(
        "--deletion-probability",
        type=float,
        default=0.08,
        help="Deletion event probability (default: %(default)s)",
    )
    parser.add_argument(
        "--substitution-probability",
        type=float,
        default=0.08,
        help="Substitution event probability (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: %(default)s)",
    )
    parser.add_argument(
        "--lambda-gc",
        type=float,
        default=1.0,
        help="GC penalty weight for constrained decoding (default: %(default)s)",
    )
    parser.add_argument(
        "--lambda-homopolymer",
        type=float,
        default=1.0,
        help="Homopolymer penalty weight for constrained decoding (default: %(default)s)",
    )
    parser.add_argument(
        "--ai-analysis",
        action="store_true",
        help=(
            "Use the optional GPT-5.6 analyst; requires the 'ai' extra and a maintainer-provided "
            "OPENAI_API_KEY"
        ),
    )
    parser.add_argument(
        "--file-decoder",
        choices=SUPPORTED_DECODERS,
        default="consensus",
        help="Decoder for --input-file (default: %(default)s)",
    )
    parser.add_argument(
        "--fragment-bases",
        type=int,
        default=64,
        help="Payload bases per known file fragment (default: %(default)s)",
    )
    parser.add_argument(
        "--output-file",
        type=Path,
        help="Write verified recovered bytes here (used only with --input-file)",
    )
    return parser


def _run_file_command(parser: argparse.ArgumentParser, arguments: argparse.Namespace) -> None:
    """Run the binary file path and optionally write only integrity-verified output."""
    if arguments.ai_analysis:
        parser.error("--ai-analysis applies to --sequence experiments, not --input-file")
    try:
        payload = arguments.input_file.read_bytes()
    except OSError as error:
        parser.error(f"could not read --input-file: {error}")

    media_type = mimetypes.guess_type(arguments.input_file.name)[0] or "application/octet-stream"
    try:
        result = run_file_recovery(
            payload,
            filename=arguments.input_file.name,
            media_type=media_type,
            fragment_bases=arguments.fragment_bases,
            cluster_size=arguments.cluster_size,
            insertion_probability=arguments.insertion_probability,
            deletion_probability=arguments.deletion_probability,
            substitution_probability=arguments.substitution_probability,
            seed=arguments.seed,
            decoder=arguments.file_decoder,
            lambda_gc=arguments.lambda_gc,
            lambda_homopolymer=arguments.lambda_homopolymer,
        )
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    print(f"Input file: {arguments.input_file} ({result.original_size_bytes} bytes)")
    print(
        f"DNA representation: {result.encoded_nucleotides} nt in "
        f"{result.fragment_count} known fragments"
    )
    print(
        f"Synthetic evidence: {arguments.cluster_size} reads/fragment; "
        f"decoder={arguments.file_decoder}; seed={arguments.seed}"
    )
    print(f"Exact reconstructed fragments: {result.exact_fragment_count}/{result.fragment_count}")
    print(f"Expected SHA-256: {result.original_sha256}")

    if not result.checksum_verified or result.recovered_data is None:
        print(f"RECOVERY FAILED: {result.error}")
        raise SystemExit(1)

    print("RECOVERY VERIFIED: decoded bytes match the embedded SHA-256 digest")
    if arguments.output_file is not None:
        try:
            arguments.output_file.write_bytes(result.recovered_data)
        except OSError as error:
            parser.error(f"could not write --output-file: {error}")
        print(f"Wrote verified file: {arguments.output_file}")


def main() -> None:
    """Run and print one reproducible reconstruction experiment."""
    parser = build_parser()
    arguments = parser.parse_args()

    if arguments.output_file is not None and arguments.input_file is None:
        parser.error("--output-file requires --input-file")
    if arguments.input_file is not None:
        _run_file_command(parser, arguments)
        return

    try:
        result = run_experiment(
            source=arguments.sequence or DEFAULT_SEQUENCE,
            cluster_size=arguments.cluster_size,
            insertion_probability=arguments.insertion_probability,
            deletion_probability=arguments.deletion_probability,
            substitution_probability=arguments.substitution_probability,
            seed=arguments.seed,
            lambda_gc=arguments.lambda_gc,
            lambda_homopolymer=arguments.lambda_homopolymer,
        )
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    print(f"Original sequence ({len(result.source)} nt): {result.source}")
    print(
        "Channel probabilities: "
        f"ins={arguments.insertion_probability:.3f}, "
        f"del={arguments.deletion_probability:.3f}, "
        f"sub={arguments.substitution_probability:.3f}"
    )
    print(f"Random seed: {arguments.seed}")

    for trace_number, trace in enumerate(result.traces, start=1):
        print(f"Trace {trace_number:>2} ({len(trace):>2} nt): {trace}")

    print("\nReconstruction results")
    print(
        f"{'Method':<25} {'Edit':>4} {'NED':>7} {'Exact':>6} "
        f"{'GC%':>6} {'Max run':>7} {'Valid':>6}  Sequence"
    )
    for field in ("medoid", "consensus", "unconstrained", "constrained"):
        candidate = getattr(result, field)
        print(
            f"{candidate.label:<25} "
            f"{candidate.edit_distance:>4} "
            f"{candidate.normalized_edit_distance:>7.3f} "
            f"{str(candidate.exact_recovery):>6} "
            f"{100 * candidate.gc_fraction:>5.1f}% "
            f"{candidate.max_homopolymer_run:>7} "
            f"{str(candidate.biologically_valid):>6}  "
            f"{candidate.sequence}"
        )

    if arguments.ai_analysis:
        try:
            analysis = analyze_experiment(result)
        except Exception as error:  # noqa: BLE001 - CLI needs a clear API/runtime error
            parser.error(f"GPT-5.6 analysis failed: {error}")
        print("\nGPT-5.6 experiment analysis\n")
        print(analysis)


if __name__ == "__main__":
    main()
