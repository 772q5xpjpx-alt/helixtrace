"""Command-line experiment runner for HelixTrace."""

from __future__ import annotations

import argparse

from dna_trace_reconstruction.ai_analyst import analyze_experiment
from dna_trace_reconstruction.pipeline import run_experiment


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Reconstruct a source from a synthetic cluster of noisy DNA traces."
    )
    parser.add_argument(
        "--sequence",
        default="ACGTACGTACGT",
        help="Source DNA sequence (default: %(default)s)",
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
    return parser


def main() -> None:
    """Run and print one reproducible reconstruction experiment."""
    parser = build_parser()
    arguments = parser.parse_args()

    try:
        result = run_experiment(
            source=arguments.sequence,
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
