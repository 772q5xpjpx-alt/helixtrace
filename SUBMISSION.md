# HelixTrace

**Tagline:** Biology-aware reconstruction for noisy DNA storage

**Track:** Education

**Built with:** Codex powered by GPT-5.6 Sol, Python, Streamlit; optional OpenAI Responses API extension

## Submission links

- **Live demo:** https://helixtrace.streamlit.app
- **GitHub repository:** https://github.com/772q5xpjpx-alt/helixtrace
- **Demo video:** [PUBLIC YOUTUBE URL]
- **Codex `/feedback` Session ID:** [CODEX SESSION ID]

## Short description

HelixTrace is an interactive learning lab for reconstructing a digital DNA strand from multiple
noisy reads. It makes insertions, deletions, substitutions, alignment, biological constraints,
and reconstruction trade-offs visible. The complete public experience is free and requires no
account, API key, credits, or paid service.

## Inspiration and problem

DNA data storage is exciting, but reading stored information back is not a simple character-by-
character task. Sequencing can produce multiple corrupted copies of the same strand, with
insertions and deletions shifting every base that follows. A reconstruction can also agree with
the reads while violating practical sequence-design rules such as balanced GC content or short
homopolymer runs.

As a biotechnology student, I wanted a tool that lets a learner see those problems instead of
hiding them behind one final accuracy number. HelixTrace is a small, reproducible workbench for
asking a focused question: **when does a biological design prior help reconstruction, and when
does it hurt?**

## What it does

HelixTrace runs a complete controlled experiment in the browser:

1. It starts from a known synthetic DNA strand and generates independent noisy reads through a
   seeded insertion-deletion-substitution channel.
2. It reconstructs the strand with four transparent methods: observed trace medoid,
   alignment-aware consensus, evidence-only local search, and biology-aware local search.
3. It compares edit distance, normalized edit distance, exact recovery, agreement with the
   observed reads, GC content, maximum homopolymer run, and biological validity.
4. It lets the learner inspect the variable-length trace cluster and change the channel,
   cluster size, random seed, and biological-prior weights.
5. It turns the verified metrics into a deterministic guided interpretation—with a verdict,
   evidence, reliability warning, and next experiment—locally and at zero cost.
6. It includes a separate, optional maintainer-enabled GPT-5.6 analyst that can interpret the same
   bounded summary without changing any reconstruction or metric.

The known source is used only after reconstruction to score the candidates. The reconstruction
methods receive the noisy reads, not the answer.

## Why it fits Education

HelixTrace is designed as an explorable scientific lesson rather than a black-box predictor.
Students can change one variable, rerun with a fixed seed, see why raw positional voting fails
on insertions and deletions, and compare evidence fidelity with biological validity. The local,
deterministic explanations and measurements make the full lesson usable at zero cost. An optional
maintainer integration can add GPT-5.6 interpretation after measurement, with explicit guardrails
separating evidence from interpretation.

## How I built it

The project is a Python 3.11+ package with a Streamlit interface and a deterministic experiment
pipeline:

```text
source strand
    -> seeded categorical IDS channel
    -> noisy trace cluster
    -> trace medoid
    -> unit-cost global alignment and boundary-aware consensus
    -> equal-budget evidence-only and biology-aware local search
    -> reconstruction and biological metrics
    -> free local guided interpretation
       \-> optional maintainer branch: bounded payload -> GPT-5.6 interpretation
```

Insertions are collected at reference boundaries, while bases and gaps vote at reference
positions. Iterative consensus starts from an order-independent trace medoid and handles cycles
deterministically. The biology-aware method adds soft penalties for GC content outside 45–55%
and homopolymer runs above three bases. It is inference-time constrained search—not neural
training—and its control receives the same local-search budget without biological penalties.

Every experiment is reproducible from its seed. The repository includes machine-readable
benchmark rows and summaries, plus an automated test suite covering the channel, alignment,
reconstruction, constraints, metrics, pipeline, source generation, CLI, and GPT integration.
At submission time, all 90 tests pass.

## How Codex was used

Codex, powered by GPT-5.6 Sol for this development task, was my development partner throughout the
Build Week extension. I used the main build session to audit the original scaffold, choose a
credible minimum product, plan the architecture, implement the reconstruction and constraint
modules, write and run tests, diagnose edge cases, build the Streamlit experience, run the
controlled benchmark, and prepare the documentation and demo. Parallel Codex workstreams helped
review the repository, design the deterministic baseline, and shape the pitch, while the main
session integrated and verified the result.

This was not a one-shot code-generation prompt. I used Codex as an iterative engineering loop:
inspect, implement, test, challenge assumptions, benchmark, and revise. The required main-session
identifier is listed above and can be verified from Codex `/feedback`.

## How GPT-5.6 was used

The verified GPT-5.6 use was GPT-5.6 Sol through Codex during development. It supported the
iterative engineering loop described above: repository audit, architecture, implementation,
testing, scientific challenge, benchmark review, interface work, and submission preparation. The
main Codex `/feedback` Session ID provides the required development evidence.

The repository also contains an optional **Experiment Analyst** through the OpenAI Responses API.
If a maintainer enables it, HelixTrace serializes a compact summary containing the channel
configuration, trace lengths, candidate sequences, measured metrics, and a method note, then calls
`client.responses.create(model="gpt-5.6", ...)` with `store=False`. The path is mock-tested and
guardrailed, but its presence is not presented as evidence that a live API call occurred.

The optional analyst is instructed to use only supplied measurements, avoid recalculating metrics
or inventing results, avoid state-of-the-art claims, distinguish inference-time constrained search
from neural training, identify accuracy/validity trade-offs, state the limits of one synthetic run,
and propose one next experiment. It never replaces the local reconstruction or benchmark.

## Results

I ran a seeded benchmark on 60-base strands. The main benchmark contains 120 constraint-compliant
experiments: 20 replicates for each combination of cluster size 3, 5, or 10 and insertion,
deletion, and substitution probability 0.03 or 0.06 per event. I also ran 20 GC negative controls
whose true sources intentionally violate the assumed biological prior.

For the fair comparison below, evidence-only and biology-aware search use the same candidate
neighborhood and iteration budget; only the biological penalties differ.

| Source profile | Method | Experiments | Exact recovery | Mean NED | Biologically valid |
|---|---|---:|---:|---:|---:|
| Constraint-compliant | Evidence-only | 120 | 32.5% | 0.03669 | 85% |
| Constraint-compliant | Biology-aware | 120 | 32.5% | 0.03657 | 100% |
| GC negative control | Evidence-only | 20 | 55% | 0.01078 | 0% |
| GC negative control | Biology-aware | 20 | 0% | 0.05573 | 0% |

On sources that satisfy the design assumptions, the constrained method increased valid outputs
from 85% to 100% while keeping exact recovery at 32.5%; mean NED changed only slightly, from
0.03669 to 0.03657. This small controlled benchmark does not establish statistical superiority.
The negative control is equally important: when the true source violates the GC prior, exact
recovery falls from 55% to 0% under constrained search. A biological prior can guide decoding
when it is correct, but it can systematically move the answer away from the truth when it is
wrong. HelixTrace makes that failure mode explicit.

## Challenges

- **Variable-length evidence:** insertions and deletions make raw positional majority voting
  invalid, so I needed deterministic alignment and explicit insertion-boundary handling.
- **A fair constraint comparison:** adding more optimization alone could appear to be a biology
  benefit. I built an equal-budget evidence-only control to isolate the prior's effect.
- **Scientific honesty under time pressure:** it was important not to describe local search as a
  trained neural model or turn a synthetic benchmark into a claim about real nanopore data.
- **Useful AI without outsourcing measurement:** the optional GPT-5.6 path is bounded to interpreting
  verified metrics and cannot silently invent or overwrite them.

## Accomplishments

- A working, zero-cost educational product from source generation to comparison and guided
  interpretation.
- Alignment-aware reconstruction that handles variable-length reads deterministically.
- An explainable biology-aware objective with a matched evidence-only control.
- A reproducible 140-experiment benchmark with both compliant inputs and an adversarial negative
  control.
- A polished interactive interface, CLI, machine-readable artifacts, and 90 passing tests.
- An optional GPT-5.6 integration with a narrowly defined, auditable role, mocked tests, and
  explicit scientific guardrails.

## What I learned

The most important lesson was that a prior is an assumption, not a guarantee. Aggregate validity
can improve without proving that a reconstruction is correct, and a deliberately mismatched
negative control can be more informative than another favorable example. I also learned that
reproducible seeds, matched controls, and machine-readable outputs matter as much as the visual
demo. Finally, the optional GPT-5.6 design is most useful when it sits after deterministic
measurement: it can explain evidence and suggest the next experiment without becoming the source
of that evidence.

## What's next

1. Evaluate real sequencing reads and clearly separate channel simulation from laboratory noise.
2. Add coded DNA-storage baselines and compare against appropriate trace-reconstruction systems.
3. Train a compact sequence model and test differentiable GC and homopolymer penalties, while
   retaining the current deterministic methods as controls.
4. Add confidence estimates, bootstrap intervals, and larger benchmarks across sequence lengths
   and channel conventions.
5. Let users choose a documented synthesis profile instead of assuming one universal GC window.
6. Expand the GPT-5.6 analyst into a guided experimental curriculum with saved hypotheses and
   side-by-side runs.

## Pre-existing work versus Build Week extension

The project began from a small personal research scaffold on July 10, 2026. I do not claim that
scaffold as new Build Week work. The meaningful Build Week extension was implemented on July 20,
2026 and is separated below, with the Codex session identifier providing additional evidence.

| Area | Pre-existing before the Build Week sprint | Added during the Build Week sprint |
|---|---|---|
| Research | Initial literature notes and the broad project question | Education-track framing, explicit experimental claims, limitations, and demo narrative |
| Data generation | Validated categorical IDS simulator with seeded trace-cluster generation | Constraint-compliant source generation and reproducible multi-condition benchmark runner |
| Product surface | Basic package/CLI scaffold and channel-model documentation | HelixTrace name, end-to-end pipeline, polished Streamlit application, comparison workflow, and scientific guardrails |
| Reconstruction | Not implemented | Edit metrics, trace medoid, deterministic global alignment, insertion-aware iterative consensus, evidence-only refinement, and biology-aware constrained search |
| OpenAI integration | None | GPT-5.6 Sol development through Codex, plus an optional Responses API analyst with bounded payload, prompt guardrails, CLI/UI integration, and mocked tests |
| Validation | Simulator-focused automated tests | Expanded 90-test suite, 120 compliant benchmark experiments, 20 negative controls, and committed CSV/JSON artifacts |
| Submission | None | README overhaul, submission copy, timed demo script, test instructions, and Build Week scope disclosure |

## Testing instructions

### Run the application

```bash
git clone https://github.com/772q5xpjpx-alt/helixtrace.git
cd helixtrace
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit. The simulator, reconstruction methods, metrics, and UI
form a complete experience without an OpenAI account, API key, credits, or paid service.

### Optional maintainer integration

This extension is not part of the required testing path, and judges are never asked to provide a
key. A maintainer who chooses to enable it can install the separate dependency and configure a
server-side key:

```bash
python -m pip install -e ".[ai]"
export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
streamlit run app.py
```

The OpenAI project associated with the key must have access to that model. Never commit the key.
The optional integration is mock-tested; this submission does not use its existence to claim that
a live Responses API call occurred.

### Run automated checks

```bash
python -m pip install -e ".[dev]"
pytest -q
ruff check .
```

### Reproduce the submitted benchmark

```bash
python scripts/run_benchmark.py --samples-per-cell 20 --sequence-length 60 --seed 20260720
```

The command writes long-form CSV rows and aggregate CSV/JSON summaries to `artifacts/`. The
submitted benchmark took about two minutes on the development Mac; runtime varies by machine.

## Scope and limitations

HelixTrace is a controlled, uncoded, synthetic proof of concept. It is not a state-of-the-art
claim, a clinical tool, a production DNA-storage decoder, a neural reconstruction model, or a
like-for-like evaluation against coded methods. Real nanopore generalization, alternative IDS
channel conventions, coded baselines, and trained models remain future work.
