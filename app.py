"""Interactive Streamlit demo for constraint-aware DNA trace reconstruction."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import html
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

DEFAULT_SOURCE = "ACGTGCACTGATCGTACGATCGCAACGTGCACTGATCGTACGATCGCA"
DEFAULT_CLUSTER_SIZE = 7
DEFAULT_INSERTION_PROBABILITY = 0.06
DEFAULT_DELETION_PROBABILITY = 0.06
DEFAULT_SUBSTITUTION_PROBABILITY = 0.06
DEFAULT_SEED = 42
DEFAULT_LAMBDA_GC = 1.0
DEFAULT_LAMBDA_HOMOPOLYMER = 1.0
DEFAULT_FILE_DATA = b"HELIX"
DEFAULT_FILE_NAME = "proof.txt"
DEFAULT_FILE_MEDIA_TYPE = "text/plain"
DEFAULT_FILE_SEED = 43
MAX_INTERACTIVE_FILE_BYTES = 256


st.set_page_config(
    page_title="HelixTrace · DNA trace reconstruction",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
      :root {
        --ink: #17211f;
        --muted: #65716e;
        --paper: #f7f8f4;
        --card: rgba(255, 255, 255, 0.86);
        --line: rgba(25, 57, 50, 0.13);
        --mint: #0d7c66;
        --mint-dark: #075748;
        --mint-soft: #dff3eb;
        --coral: #e87758;
        --amber: #d69a2d;
        --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        --font-mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
      }

      html, body, [class*="css"] {
        font-family: var(--font-sans);
      }

      [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(circle at 94% 3%, rgba(114, 204, 175, 0.24), transparent 25rem),
          radial-gradient(circle at 12% 55%, rgba(238, 187, 125, 0.12), transparent 28rem),
          var(--paper);
        color: var(--ink);
      }

      [data-testid="stHeader"] {
        background: transparent;
      }

      [data-testid="stToolbar"], [data-testid="stDecoration"], #MainMenu, footer {
        visibility: hidden;
      }

      [data-testid="stSidebar"] {
        background: #102f29;
        border-right: 0;
      }

      [data-testid="stSidebar"] * {
        color: #f4fbf8;
      }

      [data-testid="stSidebar"] small,
      [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #c8ddd7 !important;
      }

      [data-testid="stSidebar"] textarea,
      [data-testid="stSidebar"] input {
        color: #173b34 !important;
        background: #f8fbf9 !important;
      }

      [data-testid="stSidebar"] textarea::placeholder,
      [data-testid="stSidebar"] input::placeholder {
        color: #73827e !important;
      }

      [data-testid="stSidebar"] [data-baseweb="slider"] div[role="slider"] {
        background: #f2b976;
      }

      [data-testid="stSidebar"] .stButton > button,
      [data-testid="stSidebar"] .stFormSubmitButton > button {
        background: #f2b976;
        color: #16332d;
        border: 0;
        border-radius: 10px;
        font-weight: 800;
        min-height: 2.85rem;
        box-shadow: 0 7px 24px rgba(0, 0, 0, 0.16);
      }

      [data-testid="stSidebar"] .stButton > button:hover,
      [data-testid="stSidebar"] .stFormSubmitButton > button:hover {
        background: #ffd39a;
        color: #102f29;
      }

      .block-container {
        max-width: 1240px;
        padding-top: 2rem;
        padding-bottom: 4rem;
      }

      .hero {
        border: 1px solid var(--line);
        border-radius: 24px;
        padding: clamp(1.5rem, 4vw, 3.2rem);
        background:
          linear-gradient(120deg, rgba(255, 255, 255, 0.96), rgba(239, 248, 242, 0.9));
        box-shadow: 0 20px 55px rgba(25, 57, 50, 0.08);
        overflow: hidden;
        position: relative;
        margin-bottom: 1.45rem;
      }

      .hero::after {
        content: "ACGT · ACGT · ACGT";
        position: absolute;
        right: -1rem;
        bottom: -0.55rem;
        font: 500 clamp(1.7rem, 5vw, 4.8rem)/1 var(--font-mono);
        color: rgba(13, 124, 102, 0.065);
        letter-spacing: 0.05em;
        white-space: nowrap;
        pointer-events: none;
      }

      .eyebrow {
        color: var(--mint);
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.13em;
        text-transform: uppercase;
        margin-bottom: 0.8rem;
      }

      .hero h1 {
        color: var(--ink);
        font-size: clamp(2.15rem, 5vw, 4.45rem);
        line-height: 0.98;
        letter-spacing: -0.055em;
        max-width: 860px;
        margin: 0 0 1rem;
      }

      .hero p {
        color: var(--muted);
        font-size: 1.05rem;
        line-height: 1.65;
        max-width: 760px;
        margin: 0;
      }

      .scope-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin-top: 1.3rem;
      }

      .scope-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.42rem;
        border: 1px solid rgba(13, 124, 102, 0.18);
        border-radius: 999px;
        padding: 0.4rem 0.72rem;
        color: var(--mint-dark);
        background: rgba(223, 243, 235, 0.68);
        font-size: 0.77rem;
        font-weight: 700;
      }

      .section-kicker {
        color: var(--mint);
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin: 1.7rem 0 0.3rem;
      }

      .section-title {
        color: var(--ink);
        font-size: 1.62rem;
        line-height: 1.15;
        letter-spacing: -0.025em;
        font-weight: 800;
        margin: 0 0 0.3rem;
      }

      .section-copy {
        color: var(--muted);
        font-size: 0.92rem;
        margin: 0 0 1rem;
      }

      .source-panel {
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        background: rgba(255, 255, 255, 0.76);
        box-shadow: 0 8px 25px rgba(25, 57, 50, 0.045);
      }

      .source-topline {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.65rem;
      }

      .source-label {
        color: var(--muted);
        font-size: 0.69rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
      }

      .source-meta {
        color: var(--muted);
        font: 500 0.72rem/1 var(--font-mono);
      }

      .dna-sequence {
        display: flex;
        flex-wrap: wrap;
        gap: 0.18rem;
        font: 500 0.91rem/1.7 var(--font-mono);
        word-break: break-all;
      }

      .nt {
        display: inline-grid;
        place-items: center;
        min-width: 1.38rem;
        height: 1.55rem;
        border-radius: 5px;
      }

      .nt-a { color: #075f50; background: #daf1e9; }
      .nt-c { color: #315f9f; background: #e3ecfa; }
      .nt-g { color: #9b6412; background: #fbefd8; }
      .nt-t { color: #a64c3d; background: #fae5df; }

      .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.85rem 0 0.2rem;
      }

      .kpi {
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        background: rgba(255, 255, 255, 0.68);
      }

      .kpi-label {
        color: var(--muted);
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .kpi-value {
        color: var(--ink);
        font-size: 1.43rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        margin-top: 0.22rem;
      }

      .pipeline-flow {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.62rem;
        margin: 1rem 0;
      }

      .pipeline-stage {
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 0.85rem;
        background: rgba(255, 255, 255, 0.75);
        min-height: 105px;
      }

      .pipeline-stage strong {
        display: block;
        color: var(--ink);
        font-size: 0.82rem;
        margin: 0.22rem 0;
      }

      .pipeline-stage span {
        color: var(--muted);
        font-size: 0.7rem;
        line-height: 1.35;
      }

      .stage-number {
        color: var(--mint) !important;
        font: 700 0.65rem/1 var(--font-mono) !important;
      }

      .integrity-panel {
        border: 1px solid rgba(13, 124, 102, 0.28);
        border-radius: 18px;
        padding: 1.1rem 1.25rem;
        background: linear-gradient(115deg, #e3f6ee, rgba(255,255,255,0.92));
        margin: 1rem 0;
      }

      .integrity-panel.failed {
        border-color: rgba(232, 119, 88, 0.38);
        background: linear-gradient(115deg, #fae9e3, rgba(255,255,255,0.92));
      }

      .hash-value {
        color: #35544d;
        font: 500 0.7rem/1.5 var(--font-mono);
        overflow-wrap: anywhere;
      }

      .selection-pill {
        display: inline-flex;
        margin: 0.25rem 0.3rem 0.25rem 0;
        border-radius: 999px;
        padding: 0.38rem 0.62rem;
        color: var(--mint-dark);
        background: var(--mint-soft);
        font: 600 0.68rem/1 var(--font-mono);
      }

      .method-card {
        height: 100%;
        min-height: 365px;
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1.15rem;
        background: var(--card);
        box-shadow: 0 10px 28px rgba(25, 57, 50, 0.055);
      }

      .method-card.featured {
        border-color: rgba(13, 124, 102, 0.45);
        box-shadow: 0 14px 34px rgba(13, 124, 102, 0.12);
      }

      .method-number {
        color: var(--mint);
        font: 500 0.7rem/1 var(--font-mono);
        letter-spacing: 0.08em;
        margin-bottom: 0.6rem;
      }

      .method-title {
        color: var(--ink);
        font-size: 1.15rem;
        font-weight: 800;
        letter-spacing: -0.025em;
      }

      .method-description {
        color: var(--muted);
        font-size: 0.78rem;
        min-height: 2.5rem;
        margin: 0.18rem 0 0.7rem;
      }

      .method-sequence {
        border-radius: 9px;
        padding: 0.66rem;
        background: #f0f4ef;
        color: #25453e;
        font: 500 0.72rem/1.65 var(--font-mono);
        min-height: 4.2rem;
        word-break: break-all;
      }

      .badges {
        display: flex;
        flex-wrap: wrap;
        gap: 0.38rem;
        margin: 0.75rem 0;
      }

      .badge {
        border-radius: 999px;
        padding: 0.32rem 0.55rem;
        font-size: 0.65rem;
        font-weight: 800;
      }

      .badge-good { color: #075748; background: #dff3eb; }
      .badge-warn { color: #8c5710; background: #f9ecd2; }
      .badge-neutral { color: #596360; background: #ecefed; }

      .metric-list {
        border-top: 1px solid var(--line);
        margin-top: 0.2rem;
      }

      .metric-row {
        display: flex;
        justify-content: space-between;
        gap: 0.7rem;
        border-bottom: 1px solid var(--line);
        padding: 0.48rem 0;
        color: var(--muted);
        font-size: 0.76rem;
      }

      .metric-row strong {
        color: var(--ink);
        font: 500 0.75rem/1 var(--font-mono);
      }

      .quality-panel {
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 1rem 1.1rem;
        background: rgba(255, 255, 255, 0.68);
        margin-top: 0.9rem;
      }

      .quality-row {
        display: grid;
        grid-template-columns: 145px 1fr 48px;
        align-items: center;
        gap: 0.75rem;
        margin: 0.68rem 0;
      }

      .quality-label {
        color: var(--ink);
        font-size: 0.77rem;
        font-weight: 700;
      }

      .quality-track {
        height: 8px;
        border-radius: 999px;
        background: #e6ebe7;
        overflow: hidden;
      }

      .quality-fill {
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, #65bca6, #0d7c66);
      }

      .quality-value {
        color: var(--muted);
        font: 500 0.7rem/1 var(--font-mono);
        text-align: right;
      }

      .trace-list {
        display: grid;
        gap: 0.4rem;
        margin-top: 0.65rem;
      }

      .trace-row {
        display: grid;
        grid-template-columns: 54px minmax(0, 1fr) 62px;
        align-items: center;
        gap: 0.6rem;
        border: 1px solid var(--line);
        border-radius: 9px;
        padding: 0.52rem 0.72rem;
        background: rgba(255, 255, 255, 0.66);
      }

      .trace-id, .trace-length {
        color: var(--muted);
        font: 500 0.67rem/1 var(--font-mono);
      }

      .trace-length { text-align: right; }

      .trace-sequence {
        color: #27453f;
        font: 500 0.72rem/1.35 var(--font-mono);
        overflow-wrap: anywhere;
      }

      .method-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: rgba(255,255,255,0.66);
        font-size: 0.78rem;
      }

      .method-table th, .method-table td {
        padding: 0.72rem 0.78rem;
        text-align: left;
        border-bottom: 1px solid var(--line);
      }

      .method-table th {
        color: var(--muted);
        background: #edf2ee;
        font-size: 0.66rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
      }

      .method-table td { color: var(--ink); }
      .method-table tr:last-child td { border-bottom: 0; }

      .analyst-panel {
        border: 1px solid rgba(13, 124, 102, 0.23);
        border-radius: 18px;
        padding: 1.1rem 1.25rem;
        background: linear-gradient(115deg, #e7f5ef, rgba(255,255,255,0.9));
        margin-top: 0.7rem;
      }

      .analyst-model {
        display: inline-flex;
        border-radius: 999px;
        padding: 0.3rem 0.55rem;
        background: #0d7c66;
        color: white;
        font: 500 0.65rem/1 var(--font-mono);
      }

      .sidebar-brand {
        font-size: 1.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        padding: 0.3rem 0 0.1rem;
      }

      .sidebar-note {
        color: #bdd3cd;
        font-size: 0.74rem;
        line-height: 1.55;
        margin-bottom: 0.8rem;
      }

      .sidebar-rule {
        height: 1px;
        background: rgba(255,255,255,0.12);
        margin: 0.75rem 0 1rem;
      }

      .footer-note {
        color: var(--muted);
        text-align: center;
        font-size: 0.72rem;
        padding-top: 2rem;
      }

      @media (max-width: 900px) {
        .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .pipeline-flow { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .quality-row { grid-template-columns: 110px 1fr 42px; }
      }

      @media (max-width: 620px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .kpi-grid { grid-template-columns: 1fr 1fr; }
        .trace-row { grid-template-columns: 44px minmax(0, 1fr); }
        .trace-length { display: none; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


try:
    from dna_trace_reconstruction.ai_analyst import (
        DEFAULT_MODEL,
        analyze_experiment,
        has_openai_api_key,
        interpret_experiment_locally,
    )
    from dna_trace_reconstruction.file_pipeline import run_file_recovery
    from dna_trace_reconstruction.pipeline import run_experiment
except ImportError as import_error:
    st.error(
        "The reconstruction modules are not available yet. Install the project and restart "
        f"the app. Technical detail: {import_error}"
    )
    st.stop()


def _value(item: Any, name: str, default: Any = None) -> Any:
    """Read one result field from a dataclass-like object or mapping."""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _clean_sequence(raw_sequence: str) -> str:
    """Normalize user-entered DNA without silently changing bases."""
    return "".join(raw_sequence.split()).upper()


def _longest_homopolymer(sequence: str) -> int:
    """Return the longest identical-base run in a sequence."""
    if not sequence:
        return 0
    longest = 1
    current = 1
    for previous, base in zip(sequence, sequence[1:], strict=False):
        if base == previous:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _gc_fraction(sequence: str) -> float:
    """Calculate GC fraction for lightweight input validation."""
    if not sequence:
        return 0.0
    return sum(base in "GC" for base in sequence) / len(sequence)


def _dna_markup(sequence: str) -> str:
    """Render a validated DNA sequence as color-coded nucleotide cells."""
    return "".join(
        f'<span class="nt nt-{base.lower()}">{html.escape(base)}</span>' for base in sequence
    )


def _format_number(value: Any, decimals: int = 3) -> str:
    """Format numeric metrics defensively for the UI."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    return f"{number:.{decimals}f}"


def _compact_html(markup: str) -> str:
    """Remove Markdown-significant indentation from generated HTML fragments."""
    return "".join(line.strip() for line in markup.splitlines())


def _method_card(
    evaluation: Any,
    *,
    number: str,
    title: str,
    description: str,
    featured: bool = False,
) -> str:
    """Build one complete reconstruction method card."""
    sequence = str(_value(evaluation, "sequence", ""))
    exact = bool(_value(evaluation, "exact_recovery", False))
    valid = bool(_value(evaluation, "biologically_valid", False))
    gc_fraction = _value(evaluation, "gc_fraction", 0.0)
    max_run = _value(evaluation, "max_homopolymer_run", 0)
    edit_distance = _value(evaluation, "edit_distance", 0)
    normalized_distance = _value(evaluation, "normalized_edit_distance", 0.0)
    evidence_cost = _value(evaluation, "evidence_cost", 0.0)

    recovery_badge = (
        '<span class="badge badge-good">Exact recovery</span>'
        if exact
        else '<span class="badge badge-neutral">Approximate</span>'
    )
    biology_badge = (
        '<span class="badge badge-good">Biology valid</span>'
        if valid
        else '<span class="badge badge-warn">Constraint violation</span>'
    )
    featured_class = " featured" if featured else ""

    return _compact_html(f"""
      <div class="method-card{featured_class}">
        <div class="method-number">METHOD {html.escape(number)}</div>
        <div class="method-title">{html.escape(title)}</div>
        <div class="method-description">{html.escape(description)}</div>
        <div class="method-sequence">{html.escape(sequence)}</div>
        <div class="badges">{recovery_badge}{biology_badge}</div>
        <div class="metric-list">
          <div class="metric-row"><span>Edit distance</span><strong>{html.escape(str(edit_distance))}</strong></div>
          <div class="metric-row"><span>Normalized distance</span><strong>{_format_number(normalized_distance)}</strong></div>
          <div class="metric-row"><span>GC content</span><strong>{_format_number(100 * float(gc_fraction), 1)}%</strong></div>
          <div class="metric-row"><span>Longest homopolymer</span><strong>{html.escape(str(max_run))} nt</strong></div>
          <div class="metric-row"><span>Read evidence cost</span><strong>{_format_number(evidence_cost, 2)}</strong></div>
        </div>
      </div>
    """)


def _quality_panel(methods: list[tuple[str, Any]]) -> str:
    """Visualize reconstruction similarity as compact progress tracks."""
    rows: list[str] = []
    for label, evaluation in methods:
        normalized_distance = float(_value(evaluation, "normalized_edit_distance", 1.0))
        similarity = max(0.0, min(1.0, 1.0 - normalized_distance))
        rows.append(
            f"""
            <div class="quality-row">
              <div class="quality-label">{html.escape(label)}</div>
              <div class="quality-track"><div class="quality-fill" style="width:{100 * similarity:.1f}%"></div></div>
              <div class="quality-value">{100 * similarity:.1f}%</div>
            </div>
            """
        )
    return _compact_html('<div class="quality-panel">' + "".join(rows) + "</div>")


def _trace_list(traces: list[str], source_length: int) -> str:
    """Build a bounded, readable trace-cluster list."""
    rows: list[str] = []
    for index, trace in enumerate(traces, start=1):
        delta = len(trace) - source_length
        delta_label = f"{delta:+d} nt"
        rows.append(
            f"""
            <div class="trace-row">
              <div class="trace-id">READ {index:02d}</div>
              <div class="trace-sequence">{html.escape(trace)}</div>
              <div class="trace-length">{len(trace)} nt · {delta_label}</div>
            </div>
            """
        )
    return _compact_html('<div class="trace-list">' + "".join(rows) + "</div>")


def _comparison_table(methods: list[tuple[str, Any]]) -> str:
    """Build a dependency-free method comparison table."""
    rows: list[str] = []
    for label, evaluation in methods:
        exact = "Yes" if _value(evaluation, "exact_recovery", False) else "No"
        valid = "Yes" if _value(evaluation, "biologically_valid", False) else "No"
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(label)}</strong></td>"
            f"<td>{html.escape(str(_value(evaluation, 'edit_distance', '—')))}</td>"
            f"<td>{_format_number(_value(evaluation, 'normalized_edit_distance'))}</td>"
            f"<td>{_format_number(100 * float(_value(evaluation, 'gc_fraction', 0.0)), 1)}%</td>"
            f"<td>{html.escape(str(_value(evaluation, 'max_homopolymer_run', '—')))}</td>"
            f"<td>{valid}</td>"
            f"<td>{exact}</td>"
            "</tr>"
        )
    return _compact_html(f"""
      <table class="method-table">
        <thead>
          <tr>
            <th>Method</th><th>Edit distance</th><th>Normalized</th><th>GC</th>
            <th>Max run</th><th>Valid</th><th>Exact</th>
          </tr>
        </thead>
        <tbody>{"".join(rows)}</tbody>
      </table>
    """)


def _run_configuration(configuration: dict[str, Any]) -> Any | None:
    """Execute the pipeline while keeping failures visible and recoverable."""
    try:
        with st.spinner("Simulating noisy reads and reconstructing the strand…"):
            return run_experiment(**configuration)
    except Exception as error:  # Streamlit must surface pipeline failures instead of crashing.
        st.error(f"The experiment could not be completed: {error}")
        return None


def _run_file_configuration(
    data: bytes,
    filename: str,
    media_type: str,
    configuration: dict[str, Any],
) -> Any | None:
    """Run the file pipeline and keep validation failures inside the product UI."""
    try:
        with st.spinner("Encoding bytes, simulating reads, and reconstructing every fragment…"):
            return run_file_recovery(
                data,
                filename=filename,
                media_type=media_type,
                **configuration,
            )
    except Exception as error:  # Streamlit must remain usable after invalid uploads/settings.
        st.error(f"The file recovery run could not be completed: {error}")
        return None


def _file_pipeline_markup(result: Any) -> str:
    """Build the five-stage file recovery flow from a completed result."""
    checksum_verified = bool(_value(result, "checksum_verified", False))
    config = _value(result, "config")
    decoder = str(_value(config, "decoder", "—"))
    verification = "SHA-256 match" if checksum_verified else "Integrity failure"
    return _compact_html(f"""
      <div class="pipeline-flow">
        <div class="pipeline-stage"><span class="stage-number">01</span><strong>Frame bytes</strong><span>{_value(result, "original_size_bytes", 0)} B + versioned metadata</span></div>
        <div class="pipeline-stage"><span class="stage-number">02</span><strong>Encode DNA</strong><span>{_value(result, "encoded_nucleotides", 0)} nt · exact 50% GC</span></div>
        <div class="pipeline-stage"><span class="stage-number">03</span><strong>Simulate reads</strong><span>{_value(result, "fragment_count", 0)} known clusters · {_value(config, "cluster_size", 0)} reads each</span></div>
        <div class="pipeline-stage"><span class="stage-number">04</span><strong>Reconstruct</strong><span>{html.escape(decoder)} · source-free inference</span></div>
        <div class="pipeline-stage"><span class="stage-number">05</span><strong>Verify file</strong><span>{html.escape(verification)}</span></div>
      </div>
    """)


def _learned_selection_markup(fragments: list[Any]) -> str:
    """Summarize which upstream candidate the learned model selected."""
    counts = Counter(str(_value(fragment, "selected_method", "unknown")) for fragment in fragments)
    labels = {
        "medoid": "medoid",
        "consensus": "consensus",
        "unconstrained": "evidence",
        "constrained": "biology",
    }
    return "".join(
        f'<span class="selection-pill">{html.escape(labels.get(name, name))}: {count}</span>'
        for name, count in sorted(counts.items())
    )


st.markdown(
    """
    <section class="hero">
      <div class="eyebrow">DNA data storage · file recovery engine</div>
      <h1>Recover real files from noisy DNA reads.</h1>
      <p>
        Turn bytes into synthesis-aware DNA fragments, simulate insertion, deletion, and
        substitution errors, reconstruct every fragment, and accept the file only when its
        SHA-256 integrity check passes.
      </p>
      <div class="scope-strip">
        <span class="scope-pill">● Any small binary file</span>
        <span class="scope-pill">● 50% GC constrained code</span>
        <span class="scope-pill">● Learned candidate reranker</span>
        <span class="scope-pill">● Cryptographic verification</span>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown('<div class="sidebar-brand">🧬 HelixTrace</div>', unsafe_allow_html=True)
    workspace = st.radio(
        "Workspace",
        ("File recovery", "Strand sandbox"),
        label_visibility="collapsed",
    )
    st.markdown(
        '<div class="sidebar-note">Run a complete recovery or inspect one reconstruction '
        "experiment. Every result is deterministic for the selected seed.</div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)

    if workspace == "File recovery":
        decoder_labels = {
            "Learned candidate reranker": "learned",
            "Alignment consensus · fast": "consensus",
            "Evidence-only refinement": "evidence",
            "Biology-aware refinement": "biology",
            "Observed medoid · baseline": "medoid",
        }
        with st.form("file_controls"):
            uploaded_file = st.file_uploader(
                "Small file to recover",
                help=f"Any file type, up to {MAX_INTERACTIVE_FILE_BYTES} bytes in this demo.",
                max_upload_size=1,
            )
            st.caption(f"No upload? The built-in {DEFAULT_FILE_NAME} sample will be used.")
            decoder_label = st.selectbox("Decoder", tuple(decoder_labels))
            file_cluster_size = st.slider(
                "Reads per fragment",
                min_value=3,
                max_value=15,
                value=11,
                step=1,
            )
            file_error_probability = st.slider(
                "Probability per IDS event",
                min_value=0.0,
                max_value=0.05,
                value=0.01,
                step=0.005,
                format="%.3f",
            )
            file_seed = st.number_input(
                "Random seed",
                min_value=0,
                max_value=1_000_000,
                value=DEFAULT_FILE_SEED,
                key="file_seed",
            )
            file_submitted = st.form_submit_button(
                "Encode, simulate & recover",
                use_container_width=True,
            )
    else:
        with st.form("experiment_controls"):
            source_input = st.text_area(
                "Source DNA",
                value=DEFAULT_SOURCE,
                height=112,
                help="Whitespace is removed and bases are converted to uppercase.",
            )
            cluster_size = st.slider(
                "Trace cluster size",
                min_value=3,
                max_value=15,
                value=DEFAULT_CLUSTER_SIZE,
                step=1,
            )
            st.markdown("**IDS event probabilities**")
            insertion_probability = st.slider(
                "Insertion",
                min_value=0.0,
                max_value=0.2,
                value=DEFAULT_INSERTION_PROBABILITY,
                step=0.01,
                format="%.2f",
            )
            deletion_probability = st.slider(
                "Deletion",
                min_value=0.0,
                max_value=0.2,
                value=DEFAULT_DELETION_PROBABILITY,
                step=0.01,
                format="%.2f",
            )
            substitution_probability = st.slider(
                "Substitution",
                min_value=0.0,
                max_value=0.2,
                value=DEFAULT_SUBSTITUTION_PROBABILITY,
                step=0.01,
                format="%.2f",
            )
            seed = st.number_input(
                "Random seed", min_value=0, max_value=1_000_000, value=DEFAULT_SEED
            )

            st.markdown("**Biological prior weights**")
            lambda_gc = st.slider(
                "GC-content weight (λGC)",
                min_value=0.0,
                max_value=5.0,
                value=DEFAULT_LAMBDA_GC,
                step=0.1,
                format="%.1f",
            )
            lambda_homopolymer = st.slider(
                "Homopolymer weight (λHP)",
                min_value=0.0,
                max_value=5.0,
                value=DEFAULT_LAMBDA_HOMOPOLYMER,
                step=0.1,
                format="%.1f",
            )
            submitted = st.form_submit_button("Run experiment", use_container_width=True)


if workspace == "File recovery":
    if uploaded_file is None:
        file_data = DEFAULT_FILE_DATA
        file_name = DEFAULT_FILE_NAME
        file_media_type = DEFAULT_FILE_MEDIA_TYPE
    else:
        file_data = uploaded_file.getvalue()
        file_name = uploaded_file.name or "recovered-file.bin"
        file_media_type = uploaded_file.type or "application/octet-stream"

    selected_decoder = decoder_labels[decoder_label]
    file_run_signature = (
        hashlib.sha256(file_data).hexdigest(),
        file_name,
        file_media_type,
        selected_decoder,
        int(file_cluster_size),
        float(file_error_probability),
        int(file_seed),
    )

    st.markdown('<div class="section-kicker">End-to-end recovery</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-title">From file bytes to verified bytes again</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="section-copy">The decoder sees only noisy read clusters. The original is retained solely to score this controlled simulation after reconstruction.</div>',
        unsafe_allow_html=True,
    )

    if len(file_data) > MAX_INTERACTIVE_FILE_BYTES:
        st.error(
            f"This free interactive demo accepts up to {MAX_INTERACTIVE_FILE_BYTES} bytes; "
            f"the selected file contains {len(file_data)} bytes. Choose a smaller proof file."
        )
        st.stop()

    if file_submitted:
        file_configuration = {
            "fragment_bases": 40 if selected_decoder == "learned" else 64,
            "cluster_size": int(file_cluster_size),
            "insertion_probability": float(file_error_probability),
            "deletion_probability": float(file_error_probability),
            "substitution_probability": float(file_error_probability),
            "seed": int(file_seed),
            "decoder": selected_decoder,
            "local_search_steps": 1,
        }
        file_result = _run_file_configuration(
            file_data,
            file_name,
            file_media_type,
            file_configuration,
        )
        if file_result is not None:
            st.session_state["file_recovery_result"] = file_result
            st.session_state["file_recovery_signature"] = file_run_signature

    file_result = (
        st.session_state.get("file_recovery_result")
        if st.session_state.get("file_recovery_signature") == file_run_signature
        else None
    )
    if file_result is None:
        st.markdown(
            """
            **What will happen when you run it**

            1. A versioned frame stores the file bytes, metadata, and SHA-256 digest.
            2. A reversible constrained code emits exactly 50% GC DNA with no adjacent repeats.
            3. Each fragment produces a cluster of synthetic reads with IDS errors.
            4. The selected source-free decoder reconstructs every fragment.
            5. A download appears only if the decoded file passes its embedded SHA-256 check.
            """
        )
        st.info("Use the built-in proof file or upload a small file, then start the recovery.")
        st.stop()

    file_fragments = list(_value(file_result, "fragments", []))
    file_config = _value(file_result, "config")
    exact_fragments = int(_value(file_result, "exact_fragment_count", 0))
    fragment_count = int(_value(file_result, "fragment_count", len(file_fragments)))
    st.markdown(_file_pipeline_markup(file_result), unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi"><div class="kpi-label">Input</div><div class="kpi-value">{_value(file_result, "original_size_bytes", 0)} B</div></div>
          <div class="kpi"><div class="kpi-label">DNA payload</div><div class="kpi-value">{_value(file_result, "encoded_nucleotides", 0)} nt</div></div>
          <div class="kpi"><div class="kpi-label">Exact fragments</div><div class="kpi-value">{exact_fragments}/{fragment_count}</div></div>
          <div class="kpi"><div class="kpi-label">Total reads</div><div class="kpi-value">{fragment_count * int(_value(file_config, "cluster_size", 0))}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    checksum_verified = bool(_value(file_result, "checksum_verified", False))
    integrity_class = "integrity-panel" if checksum_verified else "integrity-panel failed"
    integrity_title = "✓ Exact file recovered" if checksum_verified else "✕ Corruption detected"
    integrity_copy = (
        "The reconstructed bytes match the digest stored before the noisy channel."
        if checksum_verified
        else "At least one fragment remained wrong, so HelixTrace refused to expose an unverified download."
    )
    st.markdown(
        f"""
        <div class="{integrity_class}">
          <strong>{integrity_title}</strong>
          <p style="color:#405d56; margin:0.35rem 0 0.55rem; font-size:0.82rem;">{integrity_copy}</p>
          <div class="hash-value">SHA-256 · {html.escape(str(_value(file_result, "original_sha256", "—")))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if str(_value(file_config, "decoder", "")) == "learned":
        st.markdown("**Learned selector decisions across fragments**")
        st.markdown(_learned_selection_markup(file_fragments), unsafe_allow_html=True)
        agreement_count = sum(
            _value(fragment, "candidate_variants") == 1 for fragment in file_fragments
        )
        st.caption(
            "helixtrace-linear-reranker-v1 · trained on 80 synthetic experiments; evaluated "
            "on a separate 120-experiment seed split. It selects among four upstream candidates. "
            f"All candidates agreed on {agreement_count}/{fragment_count} fragments in this run; "
            "identical-candidate ties use a deterministic method label."
        )

    if checksum_verified and _value(file_result, "recovered_data") is not None:
        st.download_button(
            "Download verified recovered file",
            data=_value(file_result, "recovered_data"),
            file_name=str(_value(file_result, "recovered_filename", file_name) or file_name),
            mime=str(
                _value(file_result, "recovered_media_type", file_media_type) or file_media_type
            ),
            type="primary",
            use_container_width=True,
        )
    elif recovery_error := _value(file_result, "error"):
        st.warning(str(recovery_error))
        st.caption("Try more reads, a lower error rate, or a different deterministic seed.")

    if file_fragments:
        st.markdown('<div class="section-kicker">Read-level evidence</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-title">Open one reconstructed fragment</div>',
            unsafe_allow_html=True,
        )
        inspected_index = st.selectbox(
            "Fragment",
            range(len(file_fragments)),
            format_func=lambda index: f"Fragment {index + 1} of {len(file_fragments)}",
        )
        inspected = file_fragments[int(inspected_index)]
        inspected_traces = list(_value(inspected, "traces", []))
        source_column, read_column, recovered_column = st.columns(3)
        with source_column:
            st.caption("Synthetic ground truth · evaluation only")
            st.code(str(_value(inspected, "source", "")), language=None)
        with read_column:
            st.caption("One noisy observed read")
            st.code(str(inspected_traces[0] if inspected_traces else ""), language=None)
        with recovered_column:
            st.caption(f"Recovered · {_value(inspected, 'selected_method', 'decoder')}")
            st.code(str(_value(inspected, "reconstructed", "")), language=None)

    with st.expander("Scientific scope and production gaps"):
        st.markdown(
            """
            - **Synthetic channel:** the reads are simulated locally; this release is not validated on nanopore data.
            - **Known clusters and order:** fragment identity, orientation, and ordering are supplied out of band. Demultiplexing and clustering are separate unsolved layers here.
            - **No error-correcting code:** multiple reads provide reconstruction evidence; SHA-256 detects remaining corruption but cannot repair it.
            - **Constrained encoder:** the default reversible code guarantees 50% GC and homopolymer length one at a density of 1 bit/nt, before primers or addressing overhead.
            - **Small learned model:** the ridge reranker selects among four deterministic candidates. Held-out exact recovery did not improve over the strongest fixed candidate, while mean NED improved by 0.33% (one edit across 120 experiments).
            - **Prototype scale:** the UI intentionally caps files at 256 bytes. Movies and large images are the long-term application, not a capability claimed by this demo.
            """
        )

    st.markdown(
        '<div class="footer-note">HelixTrace · Verified, source-free reconstruction for controlled DNA-storage experiments</div>',
        unsafe_allow_html=True,
    )
    st.stop()


source = _clean_sequence(source_input)
probability_sum = insertion_probability + deletion_probability + substitution_probability
configuration = {
    "source": source,
    "cluster_size": int(cluster_size),
    "insertion_probability": float(insertion_probability),
    "deletion_probability": float(deletion_probability),
    "substitution_probability": float(substitution_probability),
    "seed": int(seed),
    "lambda_gc": float(lambda_gc),
    "lambda_homopolymer": float(lambda_homopolymer),
}

validation_error: str | None = None
if not source:
    validation_error = "Enter a source DNA sequence."
elif set(source) - set("ACGT"):
    invalid = ", ".join(sorted(set(source) - set("ACGT")))
    validation_error = f"Source DNA contains invalid symbols: {invalid}. Use only A, C, G, and T."
elif not 4 <= len(source) <= 200:
    validation_error = "For this interactive demo, use a source strand between 4 and 200 bases."
elif probability_sum > 1.0:
    validation_error = "Insertion, deletion, and substitution probabilities must sum to 1 or less."

should_run = submitted or "experiment_result" not in st.session_state
if should_run:
    if validation_error:
        st.error(validation_error)
    else:
        experiment_result = _run_configuration(configuration)
        if experiment_result is not None:
            st.session_state["experiment_result"] = experiment_result
            st.session_state["experiment_configuration"] = configuration
            st.session_state.pop("ai_analysis", None)
            st.session_state.pop("guided_analysis", None)

result = st.session_state.get("experiment_result")
active_configuration = st.session_state.get("experiment_configuration", configuration)

if result is None:
    st.info("Choose a valid source strand and run the experiment to see reconstruction results.")
    st.stop()

result_source = str(_value(result, "source", active_configuration["source"]))
traces = list(_value(result, "traces", []))
medoid = _value(result, "medoid")
consensus = _value(result, "consensus")
constrained = _value(result, "constrained")
unconstrained = _value(result, "unconstrained")
methods = [
    ("Observed medoid", medoid),
    ("Aligned consensus", consensus),
    ("Evidence-only search", unconstrained),
    ("Biology-aware", constrained),
]

source_gc = _gc_fraction(result_source)
source_max_run = _longest_homopolymer(result_source)
source_valid = 0.45 <= source_gc <= 0.55 and source_max_run <= 3
if not source_valid:
    st.warning(
        "This source lies outside the experiment's biological design assumption "
        "(GC 45–55% and homopolymers ≤3). The biology-aware method may prefer a valid strand "
        "over the supplied ground truth."
    )

st.markdown('<div class="section-kicker">01 · Experiment snapshot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">Known source and channel conditions</div>', unsafe_allow_html=True
)
st.markdown(
    '<div class="section-copy">The source is visible here for evaluation only; reconstruction methods receive the noisy cluster.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    f"""
    <div class="source-panel">
      <div class="source-topline">
        <div class="source-label">Ground-truth strand</div>
        <div class="source-meta">{len(result_source)} nt · GC {100 * source_gc:.1f}% · max run {source_max_run}</div>
      </div>
      <div class="dna-sequence">{_dna_markup(result_source)}</div>
    </div>
    <div class="kpi-grid">
      <div class="kpi"><div class="kpi-label">Trace cluster</div><div class="kpi-value">{len(traces)} reads</div></div>
      <div class="kpi"><div class="kpi-label">IDS event mass</div><div class="kpi-value">{100 * sum(active_configuration[key] for key in ("insertion_probability", "deletion_probability", "substitution_probability")):.0f}%</div></div>
      <div class="kpi"><div class="kpi-label">GC prior weight</div><div class="kpi-value">{active_configuration["lambda_gc"]:.1f}</div></div>
      <div class="kpi"><div class="kpi-label">HP prior weight</div><div class="kpi-value">{active_configuration["lambda_homopolymer"]:.1f}</div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-kicker">02 · Reconstruction</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">Four strategies, one noisy cluster</div>', unsafe_allow_html=True
)
st.markdown(
    '<div class="section-copy">The final pair uses the same local-search budget, isolating the effect of biological penalties.</div>',
    unsafe_allow_html=True,
)

method_columns = st.columns(4, gap="small")
card_specs = [
    (
        medoid,
        "01",
        "Observed medoid",
        "The read with the lowest total edit distance to the rest of the cluster.",
        False,
    ),
    (
        consensus,
        "02",
        "Aligned consensus",
        "Gap-aware voting after progressively aligning the variable-length reads.",
        False,
    ),
    (
        unconstrained,
        "03",
        "Evidence-only search",
        "Local candidate search scored only by agreement with the observed reads.",
        False,
    ),
    (
        constrained,
        "04",
        "Biology-aware search",
        "The same search budget, adding GC and homopolymer penalties to the score.",
        True,
    ),
]
for column, (evaluation, number, title, description, featured) in zip(
    method_columns, card_specs, strict=True
):
    with column:
        st.markdown(
            _method_card(
                evaluation,
                number=number,
                title=title,
                description=description,
                featured=featured,
            ),
            unsafe_allow_html=True,
        )

st.markdown("**Sequence similarity to the hidden source**")
st.markdown(_quality_panel(methods), unsafe_allow_html=True)

st.markdown('<div class="section-kicker">03 · Evidence</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">Inspect the traces and compare metrics</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="section-copy">Length shifts expose insertions and deletions; substitutions preserve length but change identity.</div>',
    unsafe_allow_html=True,
)

trace_tab, table_tab = st.tabs(["Noisy trace cluster", "Method comparison"])
with trace_tab:
    st.markdown(_trace_list(traces, len(result_source)), unsafe_allow_html=True)
with table_tab:
    st.markdown(_comparison_table(methods), unsafe_allow_html=True)

st.markdown('<div class="section-kicker">04 · Guided interpretation</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-title">Turn the metrics into an experiment story</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="analyst-panel">
      <span class="analyst-model">Built with Codex · GPT-5.6 Sol</span>
      <p style="color:#405d56; margin:0.65rem 0 0; font-size:0.86rem; line-height:1.55;">
        Generate a deterministic explanation from the verified metrics. This public path runs
        locally, requires no API key, and makes no paid request. GPT-5.6 Sol in Codex helped design,
        implement, test, and document the experiment; an optional live Responses API path remains
        available to developers who configure their own key.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.button("Generate free guided interpretation", type="primary"):
    st.session_state["guided_analysis"] = interpret_experiment_locally(result)

if guided_analysis := st.session_state.get("guided_analysis"):
    st.markdown(guided_analysis)

if has_openai_api_key():
    with st.expander("Optional developer mode · live GPT-5.6 API"):
        st.caption(
            "This mode uses the separately billed OpenAI API and is not required for the demo."
        )
        if st.button(f"Analyze this run live with {DEFAULT_MODEL}"):
            try:
                with st.spinner(f"{DEFAULT_MODEL} is interpreting the experiment…"):
                    st.session_state["ai_analysis"] = analyze_experiment(result)
            except Exception as error:
                st.error(f"The AI analysis could not be completed: {error}")

        if ai_analysis := st.session_state.get("ai_analysis"):
            st.markdown(ai_analysis)
else:
    st.caption(
        "Zero-cost public mode is active. The optional live API path is documented in the source "
        "but is deliberately disabled without a developer-provided key."
    )

with st.expander("Scientific scope and guardrails"):
    st.markdown(
        """
        - **Controlled synthetic data:** the source strand and IDS channel are generated locally,
          so exact recovery can be measured against known ground truth.
        - **Uncoded track:** this demo does not use a convolutional code and therefore does not
          claim a like-for-like comparison with coded methods such as TrellisBMA.
        - **Variable-length reads:** insertions and deletions are handled through alignment before
          consensus; bases are not compared by raw position.
        - **Inference-only constraints:** GC and homopolymer rules rerank candidates during search.
          They are not yet differentiable training-loss terms and are reported as a transparent
          proof of concept, not as a neural-model result.
        - **Synthetic evidence only:** real nanopore generalization and CNR benchmarking remain
          future validation work.
        """
    )

st.markdown(
    '<div class="footer-note">HelixTrace · An honest, reproducible proof of concept for DNA trace reconstruction</div>',
    unsafe_allow_html=True,
)
