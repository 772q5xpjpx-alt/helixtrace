# HelixTrace — 2:30 Demo Script

**Target runtime:** 2 minutes 30 seconds

**Format:** screen recording with continuous English voiceover

**Required prepared tabs:** HelixTrace app, README benchmark table, and the main Codex build task

## Timed script

| Time | Screen action | Voiceover |
|---|---|---|
| **0:00–0:13** | Start on the HelixTrace hero. Keep the title and scope pills visible. | “This is HelixTrace: biology-aware reconstruction for noisy DNA storage. It is an educational lab for seeing how multiple corrupted DNA reads can be turned back into one candidate strand.” |
| **0:13–0:32** | Point to the insertion, deletion, and substitution controls, cluster size, and seed. Do not change the defaults yet. | “DNA reads can contain substitutions, but also insertions and deletions that shift every later position. Here I can control all three event probabilities, the number of reads, and a random seed, so every experiment is reproducible.” |
| **0:32–0:53** | Select **Run experiment**, then scroll to the source panel and the four reconstruction cards. | “The source is visible for evaluation, but the reconstruction methods receive only the noisy traces. HelixTrace compares an observed medoid, alignment-aware consensus, evidence-only local search, and biology-aware search using the same local-search budget.” |
| **0:53–1:19** | Pause over the method cards, then show **Sequence similarity** and open **Method comparison**. Highlight exact recovery, NED, GC, max run, validity, and evidence cost. | “The final method adds soft penalties for GC outside forty-five to fifty-five percent and homopolymer runs longer than three. This is deterministic inference-time search, not a trained neural model. The table exposes both sides of the decision: distance from the hidden source, agreement with the reads, and whether the candidate satisfies the biological design assumptions.” |
| **1:19–1:43** | Switch to the README benchmark table. Highlight the two compliant rows first, then the negative-control rows. | “Across one hundred twenty compliant synthetic experiments, evidence-only and constrained search both recovered exactly thirty-two point five percent. Valid outputs rose from eighty-five to one hundred percent, while mean normalized edit distance stayed almost unchanged. But the negative control matters: when the true strand violates the GC prior, constrained exact recovery drops from fifty-five percent to zero. The prior helps only when its assumption is valid.” |
| **1:43–2:06** | Select **Generate free guided interpretation**, show its evidence and reliability warning, then switch to the main Codex build task. | “The complete public lab, including this guided experiment story, runs locally without an account, key, credits, or paid service. GPT-5.6 Sol was used through Codex throughout Build Week to audit the scaffold, design and implement the pipeline, challenge scientific assumptions, test edge cases, build the interface, and prepare this submission.” |
| **2:06–2:22** | Show a passing test result or the README Build Week table, with no secrets visible. | “The repository separates the pre-existing simulator from the Build Week extension, and the Codex feedback Session ID provides development evidence. An optional Responses API analyst remains in the code, but it is not required for the product and I am not claiming a live API call.” |
| **2:22–2:30** | Return to the HelixTrace hero or the four-method comparison. End on the product name. | “HelixTrace turns a difficult bioinformatics trade-off into an experiment a student can run, inspect, question, and reproduce.” |

## Recording checklist

### Before recording

- [ ] Start the app with `streamlit run app.py` and confirm the full page loads without errors.
- [ ] Start from an environment with no `OPENAI_API_KEY` and confirm the complete public workflow
      works without an account, key, credits, or payment.
- [ ] Keep the default run ready: 7 traces; insertion, deletion, and substitution at 0.06; seed
      42; GC and homopolymer weights at 1.0.
- [ ] Confirm the method cards and comparison table fit at the chosen browser zoom. Use roughly
      80–90% zoom if needed, but keep text readable at 1080p.
- [ ] Open the README directly at the aggregate benchmark table.
- [ ] Open the main Codex task at a clean plan or test-results view. Hide unrelated tasks,
      notifications, personal filenames, email addresses, and secrets.
- [ ] Close noisy browser tabs and disable desktop notifications.
- [ ] Rehearse the exact scrolling path once. Aim for 2:25–2:35 and never exceed 3:00.

### During recording

- [ ] Record at 1080p or higher with a clear microphone and English voiceover.
- [ ] Keep the cursor slow and intentional; pause on every metric you name.
- [ ] Show the project working, not only slides or source code.
- [ ] Generate the free guided interpretation and show its evidence and reliability warning.
- [ ] Show that GPT-5.6 Sol was used through the main Codex development task; do not imply that the
      optional Responses integration made a live call.
- [ ] State that the biological method is inference-time local search, not neural training.
- [ ] State the negative-control result; do not imply state-of-the-art or real-read performance.
- [ ] Explicitly explain how Codex was used and show the main Codex build task.

### After recording

- [ ] Trim loading silence only; do not edit the sequence of actions in a misleading way.
- [ ] Check that the final video is under 3 minutes and that all text is legible.
- [ ] Watch once with audio and once muted to confirm both narration and screen story work.
- [ ] Upload to YouTube with visibility set to **Public**.
- [ ] Add the live demo URL, GitHub URL, YouTube URL, and Codex `/feedback` Session ID to
      `SUBMISSION.md` and the final Devpost form.
- [ ] Verify the public video and repository links in a logged-out/private browser window.
