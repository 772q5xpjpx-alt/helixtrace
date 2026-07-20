# HelixTrace

**Tagline:** Source-free file recovery from noisy synthetic DNA

**Track:** Developer Tools

**Built with:** Codex powered by GPT-5.6 Sol, Python, and Streamlit; optional OpenAI Responses API
extension

## Submission links

- **Live demo:** https://helixtrace.streamlit.app
- **GitHub repository:** https://github.com/772q5xpjpx-alt/helixtrace
- **Demo video:** https://youtu.be/ZfXLHUCXbVg
- **Codex `/feedback` Session ID:** 019f4b16-2c47-7410-b4b9-1c4d41bcbef0

## Short description

HelixTrace is a free developer workbench that sends a real binary file through a controlled
DNA-storage read path: constrained DNA encoding, fragmentation, synthetic insertion/deletion/
substitution reads, source-free reconstruction, byte decoding, and SHA-256 verification. It makes
success falsifiable: the file is verified only when the reconstructed bytes match the digest stored
before the noisy channel.

## Inspiration and problem

Digital data can be encoded into synthetic DNA, but reading it back is not a simple character-by-
character operation. Insertions and deletions shift every following base; substitutions change
symbols; and each stored strand produces a cluster of imperfect reads. A useful reconstruction tool
must combine those variable-length observations without seeing the original sequence.

My original goal was not only to explain DNA storage. I wanted to build toward a system that could
recover the underlying data—an image, text, or another binary file—and clearly distinguish exact
recovery from a result that merely looks plausible. HelixTrace turns that goal into a runnable,
reproducible prototype for decoder development and benchmarking.

## What it does

HelixTrace runs an end-to-end controlled experiment in the browser:

1. It frames a small uploaded file with a version, filename, media type, payload length, payload
   SHA-256, and a digest over the preceding header, metadata, and payload.
2. It converts the frame to DNA with a constrained 1-bit/nt codec that guarantees exactly 50% GC
   content and no repeated adjacent bases.
3. It divides that DNA into source fragments up to a configurable size and generates a seeded
   cluster of variable-length IDS reads for each fragment.
4. It reconstructs every fragment from the observed reads alone, using either a fixed decoder or
   the learned candidate selector. Neither receives the original DNA.
5. It rejoins the reconstructed fragments, decodes the bytes, and reports a verified recovery only
   if the embedded SHA-256 matches.
6. It retains a strand-level sandbox and benchmark for comparing trace medoid, alignment consensus,
   evidence-only refinement, and biology-aware refinement under identical evidence and budgets.
7. It includes a small learned candidate reranker trained on a synthetic split and evaluated on a
   disjoint held-out seed. The model selects among the four existing candidates from source-free
   features; it does not generate DNA.
8. It can turn verified strand metrics into a deterministic local interpretation at zero cost. A
   separate maintainer-enabled GPT-5.6 analyst can interpret the same bounded evidence without
   changing reconstruction or success status.

The workflow accepts binary content rather than assuming text. The free interface intentionally caps
uploads at 256 bytes for interactive runtime, while the reusable codec has a 4 MiB safety limit. A
readable preview is a convenience; cryptographic equality is the actual completion criterion.

## Why it fits Developer Tools

HelixTrace is a test bench for people building or evaluating DNA-storage decoders. It supplies a
reproducible channel, source-free reconstruction API, transparent candidate baselines, reversible
file codecs, deterministic seeds, machine-readable benchmark artifacts, and an interactive failure
inspector. A developer can replace a reconstruction method while holding the input clusters and
verification criterion constant.

The public instance gives judges a complete sandbox without rebuilding or provisioning an account.
The package and automated suite provide the second path: local, inspectable, and reproducible on
macOS, Linux, and Windows with Python 3.11+.

## How I built it

The project is a Python package with a Streamlit interface and two connected experiment layers:

```text
file bytes
    -> versioned frame + SHA-256
    -> constrained-1bit-v1 DNA encoder
    -> fragments up to a configured size
    -> seeded IDS read cluster per fragment
    -> source-free fragment decoder
    -> DNA join + frame decode
    -> SHA-256 verified bytes or explicit failure

strand experiment
    -> seeded categorical IDS channel
    -> trace medoid
    -> unit-cost global alignment and boundary-aware consensus
    -> equal-budget evidence-only and biology-aware local search
    -> reconstruction and biological metrics
```

The default constrained codec is deterministic and reversible. Every two-base codeword carries two
bits, contains one GC and one AT base, and is selected using the previously emitted base. The result
is exactly 50% GC with maximum homopolymer length one at 1 bit/nt. A separate low-level direct
base-4 codec reaches 2 bits/nt but makes no biological guarantee.

The file frame has two integrity layers: a payload SHA-256 and a digest over the preceding framed
content. The lower-level codec can also package clean framed data into self-indexing oligos with
short per-oligo tags. These checks detect corruption; they are not error-correcting codes.

For reconstruction, insertions are collected at reference boundaries while bases and gaps vote at
reference positions. Iterative consensus begins from an order-independent trace medoid and handles
cycles deterministically. The biological refinement adds soft penalties for GC content outside
45–55% and homopolymers above three bases. It is an inference-time search, not neural training, and
its evidence-only control receives the same neighborhood and iteration budget.

Every experiment is reproducible from its seed. Most importantly, source-free public functions
separate reconstruction from evaluation. A known source creates the synthetic read cluster; after
that generation step, reconstruction receives only observed reads, and ground truth is consulted
again only to measure performance.

The learned component is intentionally small and inspectable. A standardized ridge regression
predicts an error-like score for each deterministic candidate from read-evidence costs, sequence
lengths, distances and agreement among candidates, biological summaries, trace disagreement,
cluster size, and method identity. Training uses known synthetic sources to create targets;
inference receives only the noisy cluster and the four candidates. The weights are committed inline
without a third-party ML runtime, and a versioned JSON artifact records their provenance and
held-out evaluation.

The reusable Python pipeline defaults to a 64-nt fragment cap and consensus decoding. The live
demo's default learned run uses a 40-nt cap and one local-search step for responsiveness; selecting a
fixed decoder uses the 64-nt cap. Each fragment result exposes which upstream method the model
selected and the model version used.

## How Codex was used

Codex, powered by GPT-5.6 Sol for the main development task, was my primary engineering partner for
the Build Week extension. I used it to audit the pre-existing scaffold and official rules, choose a
testable product boundary, implement reconstruction algorithms, write adversarial tests, run and
inspect the deterministic benchmark, build the interface, and deploy the free public application.

When I clarified that the real goal was file recovery rather than an educational presentation, I
used Codex to change the architecture without risking the working submission. It preserved the
stable version on `main`, created a separate development branch, and split bounded work across
parallel agents: one for versioned binary/DNA framing, one for the source-free file pipeline, one for
an independently validated learned-candidate experiment, and one for product documentation. The
main session integrated the pieces and reran the full verification suite.

This was an iterative engineering loop, not a one-shot generation prompt: inspect, implement, test,
challenge an assumption, benchmark, and revise. Codex accelerated the implementation and review;
the key decisions were explicit—require byte-level verification, keep the original out of the
decoder, use a constrained encoder by default, retain matched baselines and a negative control, and
state the missing production layers plainly. The main-session identifier is listed above and can be
verified through Codex `/feedback`.

## How GPT-5.6 was used

The verified GPT-5.6 use was GPT-5.6 Sol through Codex during the development workflow described
above: repository audit, architecture, implementation, testing, scientific critique, benchmark
review, browser QA, deployment, and submission preparation.

The repository also contains an optional **Experiment Analyst** through the OpenAI Responses API.
When a maintainer explicitly enables it, HelixTrace serializes a compact summary of precomputed
strand metrics and calls `client.responses.create(model="gpt-5.6", ...)` with `store=False`. The
path is mock-tested and bounded to interpretation. It cannot alter candidate sequences, recalculate
metrics, or declare file recovery. Its presence is not presented as evidence that a live API call
occurred, and judges do not need an API key or paid credits.

## Results and scientific guardrail

### End-to-end file contract

In browser QA, the final product configuration sent the built-in 5-byte proof through 22 fragment
clusters and 242 noisy reads. All 22 fragments were exact, the SHA-256 matched, and the verified
download became available.

The committed file benchmark runs 48 deterministic random 16-byte binary payloads through the
constrained encoder and consensus decoder. Every cell has 12 files; the fragment cap is 64 nt, and
insertion, deletion, and substitution each receive the listed categorical per-event probability.

| Reads/fragment | Probability for each IDS event | Full files with SHA match | Exact fragments | Mean fragment NED |
|---:|---:|---:|---:|---:|
| 7 | 0.01 | 11/12 (91.7%) | 203/204 (99.5%) | 0.0000766 |
| 7 | 0.02 | 2/12 (16.7%) | 186/204 (91.2%) | 0.0016792 |
| 11 | 0.01 | **12/12 (100%)** | **204/204 (100%)** | **0.0000000** |
| 11 | 0.02 | 9/12 (75.0%) | 201/204 (98.5%) | 0.0003064 |
| **Overall** | — | **34/48 (70.8%)** | **794/816 (97.3%)** | **0.0005155** |

The 97.3% fragment rate became only 70.8% complete-file recovery because one wrong fragment is
enough to fail SHA verification. More reads helped under these settings; doubling each IDS
probability sharply reduced success. This is a descriptive synthetic, consensus-only benchmark—not
a comparison with the learned selector or evidence of wet-lab performance. Cluster identity and
fragment order are supplied out of band. The repository commits both the JSON report and per-file
CSV.

#### Contract smoke tests

The automated suite verifies three complementary paths. These are deterministic smoke tests, not a
recovery-rate benchmark:

| Case | Channel and decoder | Outcome |
|---|---|---|
| 20-byte `DNA storage recovery` payload | 1% insertion + 1% deletion + 1% substitution, 11 reads/fragment, seed 42, consensus | Original bytes recovered; SHA-256 matched |
| 2-byte `ML` payload | Same noisy channel, 40-nt fragment cap, one search step, learned selector | Original bytes recovered; SHA-256 matched; model version recorded |
| High-noise negative control | 45% deletion + 45% substitution, one read/fragment, seed 7, medoid | Integrity failure reported; no recovered bytes exposed |

A separate zero-noise test round-trips binary values including `0x00` and `0xff` plus filename and
media type. These cases verify that the end-to-end path works and fails closed; they do not estimate
recovery performance for arbitrary files or real sequencers.

### Learned candidate selection

`helixtrace-linear-reranker-v1` was fitted on 80 synthetic experiments with master seed `20260720`
and evaluated on 120 experiments from disjoint master seed `20260721`. The distribution samples
source lengths 40/60/80, cluster sizes 3/5/7/10, and one symmetric per-event IDS probability from
0.02 through 0.07. Sources satisfy 45–55% GC and maximum homopolymer length three.

| Held-out selector | Mean edit distance | Mean NED | Exact recovery |
|---|---:|---:|---:|
| Alignment consensus | 2.2500 | 0.035646 | 34.17% |
| Evidence-only refinement | 2.0000 | 0.031628 | 35.00% |
| Biology-aware refinement | 2.0000 | 0.031767 | 35.00% |
| **Learned reranker** | **1.9917** | **0.031524** | **35.00%** |
| Candidate oracle (not available at inference) | 1.9583 | 0.031038 | 35.00% |

Relative to the strongest fixed candidate, the learned reranker reduced mean NED by 0.33% and
removed one total edit across 120 held-out experiments. Exact recovery stayed at 35%. That is a real
but tiny result from one synthetic split, not evidence of broad superiority. The model cannot create
a correction that is missing from all four upstream candidates. The committed provenance artifact
records the full distribution, selection counts, metrics, and limitations.

These are strand-candidate metrics produced with three local-search steps. They are not presented as
an end-to-end file-recovery benchmark and are separate from the faster one-step live-demo setting.

### Deterministic biology-prior guardrail

The committed deterministic benchmark contains 120 constraint-compliant experiments on 60-nt
sources: 20 replicates for each combination of cluster size 3, 5, or 10 and symmetric per-event IDS
probability 0.03 or 0.06. It also contains 20 GC negative controls whose true sources deliberately
violate the biological prior.

For the matched comparison, evidence-only and biology-aware searches use the same starting
consensus, candidate neighborhood, trace evidence, and iteration budget.

| Source profile | Method | Experiments | Exact recovery | Mean NED | Biologically valid |
|---|---|---:|---:|---:|---:|
| Constraint-compliant | Evidence-only | 120 | 32.5% | 0.03669 | 85% |
| Constraint-compliant | Biology-aware | 120 | 32.5% | 0.03657 | 100% |
| GC negative control | Evidence-only | 20 | 55% | 0.01078 | 0% |
| GC negative control | Biology-aware | 20 | 0% | 0.05573 | 0% |

On compliant sources, the prior increased valid outputs from 85% to 100% without increasing exact
recovery. On the deliberately mismatched sources, it reduced exact recovery from 55% to 0%. This
small synthetic benchmark does not establish statistical superiority. It establishes a useful
engineering guardrail: biological constraints are assumptions whose failure must be tested, not
free accuracy.

The file workflow adds a stricter product-level outcome. It attempts to move a framed binary payload
through multiple noisy read clusters and reports either SHA-256-verified bytes or an explicit
failure—never an unverified success.

## Challenges

- **Turning sequences back into data:** strand edit distance was not enough. The product needed a
  reversible file format, metadata boundaries, fragmentation, and an exact integrity criterion.
- **Variable-length evidence:** insertions and deletions invalidate raw positional voting, requiring
  explicit global alignment and insertion-boundary handling.
- **No answer leakage:** the simulator knows the source, so reconstruction and evaluation had to be
  separated at the API boundary and tested independently.
- **Biological density trade-off:** the default encoder gives strong GC/homopolymer guarantees at
  1 bit/nt, half the density of direct base-4 encoding.
- **A fair constraint comparison:** both local searches needed the same candidate neighborhood and
  compute budget so an optimization advantage could not masquerade as a biology advantage.
- **Useful ML without an inflated claim:** the trained selector produced only a one-edit aggregate
  held-out improvement and no exact-recovery gain, so it is reported as such.
- **Scientific honesty under deadline:** integrity checks are not ECC, synthetic reads are not
  nanopore reads, and grouped clusters are not a complete storage system.

## Accomplishments

- A free, runnable path from real file bytes to DNA, noisy reads, source-free reconstruction, and
  SHA-256 verification.
- A reproducible 48-file synthetic benchmark with 34 complete SHA-verified recoveries and 794/816
  exact fragments across four channel/coverage conditions.
- A reversible constrained codec with exactly 50% GC and maximum homopolymer length one.
- Alignment-aware reconstruction for variable-length read clusters.
- A reproducible baseline with a matched biology-prior ablation and a deliberately adverse control.
- A trained, dependency-free linear reranker with a disjoint synthetic held-out split and committed
  provenance artifact.
- An interactive application, command-line experiment runner, committed benchmark artifacts, and
  151 passing automated unit/integration checks.
- A narrowly scoped optional GPT-5.6 integration that cannot become the source of measured evidence.

## What I learned

The largest product lesson was that reconstruction should end in a verifiable user outcome, not a
DNA similarity score. SHA-256 turns “this candidate looks close” into a falsifiable pass/fail result.
The largest scientific lesson was that a prior is an assumption, not a guarantee: it can improve
validity without improving truth and can be destructive when mismatched. I also learned that a
biologically clean encoder has a measurable density cost, and that clustering, addressing, ECC, and
real-channel calibration cannot be hidden behind a polished interface. The reranker added another
useful lesson: a measurable ML result can be technically real yet too small to support a broad claim.

## What's next

1. Expand end-to-end file benchmarking across payload sizes, asymmetric IDS rates, random seeds,
   and every decoder.
2. Add explicit addresses, demultiplexing, fragment-loss simulation, and a documented ECC layer.
3. Evaluate on real clustered nanopore reads and estimate channel parameters from empirical data.
4. Compare appropriate coded and uncoded baselines on identical splits.
5. Train a compact sequence reconstructor and test differentiable biological constraints while
   retaining the deterministic engine as a control.
6. Add confidence estimates and failure localization instead of only a whole-file pass/fail result.

## Pre-existing work versus Build Week extension

The project began from a small personal research scaffold on **July 10, 2026**, before the OpenAI
Build Week submission period. I do not claim that scaffold as new work. The submission is the
meaningful extension implemented after the period opened, with the Codex session and dated commits
providing development evidence.

| Area | Pre-existing before Build Week | Added during Build Week |
|---|---|---|
| Research | Literature notes and the broad DNA reconstruction question | Product boundary, explicit claims, failure criteria, limitations, and demo narrative |
| Data generation | Categorical IDS simulator with seeded trace-cluster generation | Controlled source generation, multi-condition benchmark, and negative control |
| Product surface | Basic package/CLI scaffold and channel note | HelixTrace application, file-recovery workflow, guided results, browser QA, and free deployment |
| Reconstruction | Not implemented | Edit metrics, trace medoid, global alignment, iterative consensus, matched local searches, and source-free decoder API |
| File storage | Not implemented | Versioned binary frame, dense and constrained DNA codecs, fragmentation, metadata, integrity checks, and recovered-byte verification |
| Machine learning | Not implemented | Trained linear candidate reranker, source-free inference features, disjoint held-out split, and versioned provenance artifact |
| OpenAI | None | GPT-5.6 Sol development through Codex and an optional bounded Responses API analyst |
| Validation | Simulator-focused tests | 151-test suite, 48-file recovery benchmark, 120 compliant strand experiments, and 20 negative controls |
| Submission | None | English README, submission copy, demo script, testing instructions, and scope disclosure |

## Testing instructions

### Fastest path: public sandbox

Open https://helixtrace.streamlit.app. The application is public, free, and requires no account,
test credentials, API key, credits, or proprietary hardware.

Use the built-in `HELIX` proof file or upload any file up to 256 bytes, then run it through the seeded
synthetic channel. The result panel distinguishes verified byte recovery from reconstruction failure,
exposes fragment-level evidence and the learned selector's choices, and enables download only after
verification. The strand sandbox remains available for method-by-method inspection.

### Run locally

```bash
git clone https://github.com/772q5xpjpx-alt/helixtrace.git
cd helixtrace
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py
```

On Windows PowerShell, use `venv\Scripts\Activate.ps1` instead.

### Test file recovery from the CLI

```bash
python -c "from pathlib import Path; Path('sample.bin').write_bytes(b'HELIX')"
helixtrace \
  --input-file sample.bin \
  --output-file recovered.bin \
  --file-decoder learned \
  --fragment-bases 40 \
  --cluster-size 3 \
  --insertion-probability 0 \
  --deletion-probability 0 \
  --substitution-probability 0 \
  --seed 42
```

This zero-noise command is a guaranteed codec/reassembly check. The CLI exits with failure and does
not write the output path unless the decoded payload passes verification. Judges can then increase
the three IDS probabilities to exercise noisy reconstruction.

### Run automated checks

The submitted suite contains 151 tests. The verified submission run completed with all 151 passing;
Ruff lint and format checks also passed.

```bash
python -m pip install -e ".[dev]"
pytest -q
ruff check .
ruff format --check .
```

### Reproduce the committed strand benchmark

```bash
python scripts/run_benchmark.py \
  --samples-per-cell 20 \
  --sequence-length 60 \
  --seed 20260720 \
  --output-dir artifacts
```

The command writes long-form CSV rows and aggregate CSV/JSON summaries to `artifacts/`.

### Reproduce the end-to-end file benchmark

```bash
python scripts/run_file_benchmark.py
```

The default command recreates 48 deterministic 16-byte payload runs and writes the submitted JSON
and per-file CSV artifacts to `artifacts/`.

### Reproduce the learned reranker report

```bash
python scripts/train_reranker.py --output artifacts/learned_reranker_report.json
```

The default command refits the 80-experiment training split and evaluates the 120-experiment
held-out split. The exact submitted provenance and metrics are also committed at
`src/dna_trace_reconstruction/data/learned_reranker_v1.json`.

### Optional maintainer integration

This path is not required for judging. A maintainer who deliberately wants the Responses API
analyst can install the separate dependency and provide a server-side key:

```bash
python -m pip install -e ".[ai]"
export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
streamlit run app.py
```

Never commit the key. The optional path is mock-tested; this submission does not use its existence
to claim a live API call.

## Scope and limitations

HelixTrace is a controlled synthetic prototype for small binary files. It does **not** include
wet-lab synthesis, PCR, Illumina or nanopore reads, primers, adapters, barcodes, molecular
addressing, demultiplexing, automatic read clustering, fragment-loss recovery, ECC, or biochemical
structure modelling. Read clusters and fragment order are supplied as out-of-band experimental
metadata. The framing codec has a 4 MiB safety limit, but practical interactive recovery is much
smaller: the public UI caps uploads at 256 bytes. The default constrained codec is 1 bit/nt; the
denser 2-bit/nt base-4 utility is not biochemically constrained. This is not a production decoder,
clinical tool, trained neural
reconstructor, real-data evaluation, state-of-the-art claim, or like-for-like TrellisBMA comparison.
The learned component is a small candidate selector evaluated on one synthetic held-out split; it
cannot generate a repair absent from its upstream candidates.
