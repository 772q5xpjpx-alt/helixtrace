"""Optional GPT-5.6 experiment analysis for HelixTrace maintainers."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from dna_trace_reconstruction.constraints import summarize_biological_constraints

if TYPE_CHECKING:
    from dna_trace_reconstruction.pipeline import ExperimentResult

DEFAULT_MODEL = "gpt-5.6"

_ANALYST_INSTRUCTIONS = """\
You are the scientific experiment analyst inside HelixTrace, an educational workbench for
synthetic DNA-storage trace reconstruction. Analyze only the structured measurements provided.
Do not recalculate DNA metrics, invent results, claim state of the art, or describe the
biology-aware method as neural training. It is inference-only constrained local search.

Return concise Markdown with exactly these headings:
### Verdict
### Evidence
### Reliability warning
### Next experiment

Under Evidence, compare alignment consensus with biology-aware decoding and mention whether any
gain in biological validity costs reconstruction accuracy. Under Reliability warning, explain
that this is one controlled synthetic experiment and that channel probabilities are per event.
Under Next experiment, propose one specific parameter change that would be scientifically useful.
Stay under 220 words and use plain English suitable for a student presenting a hackathon demo.
"""


def has_openai_api_key(api_key: str | None = None) -> bool:
    """Return whether a non-empty OpenAI API key is available without exposing it."""
    return bool((api_key or os.environ.get("OPENAI_API_KEY", "")).strip())


def interpret_experiment_locally(result: ExperimentResult) -> str:
    """Explain verified metrics without a network request or paid API usage.

    This deterministic interpretation keeps the public educational demo fully usable at zero
    cost. GPT-5.6 remains available as an optional, separately configured live analyst.
    """
    consensus = result.consensus
    evidence_only = result.unconstrained
    biology_aware = result.constrained

    distance_change = (
        biology_aware.normalized_edit_distance - evidence_only.normalized_edit_distance
    )
    if distance_change < -1e-12:
        accuracy_effect = "improved"
        verdict = (
            "For this run, the biological prior improved reconstruction accuracy relative to the "
            "matched evidence-only search."
        )
    elif distance_change > 1e-12:
        accuracy_effect = "reduced"
        verdict = (
            "For this run, the biological prior moved the reconstruction farther from the known "
            "source than the matched evidence-only search."
        )
    else:
        accuracy_effect = "did not change"
        verdict = (
            "For this run, the biological prior changed no measured reconstruction accuracy "
            "relative to the matched evidence-only search."
        )

    validity_effect = (
        "changed the output from invalid to valid"
        if biology_aware.biologically_valid and not evidence_only.biologically_valid
        else "kept both outputs biologically valid"
        if biology_aware.biologically_valid and evidence_only.biologically_valid
        else "did not produce a biologically valid output"
    )
    source_valid = summarize_biological_constraints(result.source).valid

    if not source_valid:
        next_experiment = (
            "Repeat the same seed with both biological weights set to zero. The source violates "
            "the stated design prior, so this is a direct negative-control test of prior mismatch."
        )
    elif accuracy_effect == "reduced":
        next_experiment = (
            "Keep the seed and trace cluster fixed, then reduce both biological weights by half "
            "to test whether a weaker prior preserves validity with less accuracy cost."
        )
    else:
        next_experiment = (
            "Keep every setting fixed and increase the trace cluster by two reads to test whether "
            "additional evidence makes the constrained and unconstrained answers converge."
        )

    consensus_validity = "yes" if consensus.biologically_valid else "no"
    evidence_validity = "yes" if evidence_only.biologically_valid else "no"
    biology_validity = "yes" if biology_aware.biologically_valid else "no"

    return f"""### Verdict
{verdict} It {validity_effect}.

### Evidence
- Alignment consensus: normalized edit distance **{consensus.normalized_edit_distance:.3f}**;
  biological validity **{consensus_validity}**.
- Evidence-only search: normalized edit distance **{evidence_only.normalized_edit_distance:.3f}**;
  evidence cost **{evidence_only.evidence_cost:.2f}**; validity **{evidence_validity}**.
- Biology-aware search: normalized edit distance **{biology_aware.normalized_edit_distance:.3f}**;
  evidence cost **{biology_aware.evidence_cost:.2f}**; validity **{biology_validity}**.

### Reliability warning
This is one seeded synthetic experiment with known ground truth. The IDS probabilities are per
channel event, and this result does not establish performance on real sequencing reads.

### Next experiment
{next_experiment}
"""


def analyze_experiment(
    result: ExperimentResult,
    *,
    api_key: str | None = None,
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask GPT-5.6 to interpret a bounded, precomputed experiment summary."""
    resolved_key = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
    if not resolved_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    try:
        from openai import OpenAI
    except ImportError as error:  # pragma: no cover - depends on optional runtime package
        raise RuntimeError(
            'The OpenAI package is not installed. Run: python -m pip install -e ".[ai]"'
        ) from error

    from dna_trace_reconstruction.pipeline import compact_experiment_payload

    client = OpenAI(api_key=resolved_key)
    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        instructions=_ANALYST_INSTRUCTIONS,
        input=json.dumps(compact_experiment_payload(result), indent=2),
        max_output_tokens=700,
        safety_identifier="helixtrace-local-demo",
        store=False,
    )

    analysis = response.output_text.strip()
    if not analysis:
        raise RuntimeError("GPT-5.6 returned an empty analysis")
    return analysis
