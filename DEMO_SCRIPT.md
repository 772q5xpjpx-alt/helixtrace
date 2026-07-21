# HelixTrace demo video

**Target runtime:** 2:40<br>
**Public video:** https://youtu.be/ZfXLHUCXbVg<br>
**Audio:** Álvaro's natural voice; no synthetic narration and no copyrighted music<br>
**Visual style:** real product interaction, visible cursor, short zooms, purposeful cuts, and almost
no title cards

## Recording setup

- Record only after the redesigned build is deployed and smoke-tested at the public URL.
- Capture the successful and blocked runs as separate takes at 1920×1080, then assemble them in the
  order below. Remove processing waits, but do not fake or alter any result.
- For the successful take, use **File recovery**, the built-in 5-byte `proof.txt` (`HELIX`),
  **Learned candidate reranker**, 11 reads per fragment, 0.010 probability per IDS event, and seed
  43.
- For the blocked take, use the same built-in file with **Observed medoid · baseline**, 3 reads per
  fragment, 0.050 probability per IDS event, and seed 0.
- Prepare clean crops of the committed 48-file benchmark, the Codex section, and a terminal showing
  `151 passed` and successful Ruff checks.
- Do not show API keys, personal notifications, browser bookmarks, unrelated tabs, or the optional
  GPT analyst.

## Timed shot list and narration

| Time | What the viewer sees | Álvaro says |
|---|---|---|
| **0:00–0:11** | Cold open on the hero's noisy-read instrument. Make a quick cut to the film, image, and scientific-data use cases, then back to the hero. Add one restrained overlay: `FILE → DNA → NOISY READS → VERIFIED FILE`. | “Film masters, images, and scientific datasets may one day be preserved in synthetic DNA. But sequencing returns noisy, variable-length reads. HelixTrace tests whether the original file can still be reconstructed exactly.” |
| **0:11–0:27** | Show **File recovery** and the sidebar settings. Zoom briefly on the built-in `proof.txt` notice, learned decoder, 11 reads, 0.010 error, and seed 43. | “This is a controlled software prototype, not a wet-lab storage system. I am using the built-in five-byte HELIX proof, eleven reads per fragment, one-percent insertion, deletion, and substitution probabilities, and seed forty-three.” |
| **0:27–0:44** | Pan across the ready five-stage pipeline, return to the sidebar, and click **Encode, simulate & recover**. Keep the cursor visible and cut out the processing wait. | “HelixTrace frames the bytes with SHA-256, encodes them as constrained DNA using a deterministic one-bit-per-nucleotide codec, divides them into fragments, simulates noisy read clusters, and reconstructs each fragment without giving the decoder the source.” |
| **0:44–1:00** | Land directly on **Exact file recovered**, the matching hash, and **Download verified recovered file**. Hover over the enabled download without opening a file picker. | “The run produces twenty-two reconstructed fragments from 242 noisy reads. Every fragment is exact, the bytes match the embedded digest, and only then does HelixTrace unlock the verified download. The SHA-256 gate is the final contract.” |
| **1:00–1:18** | Briefly pass the completed stages and KPIs, then select **Fragment 4 of 22**. Zoom between the 40-base synthetic ground truth, the displayed 41-base noisy read, and the recovered 40-base sequence. | “Fragment four shows the evidence. Its displayed read contains an extra base, while the recovered forty-base candidate matches the hidden source. That source is shown only for evaluation; reconstruction never receives it.” |
| **1:18–1:42** | Show **Where ML helps**, the four candidate-method labels, and the learned-selector decisions. Use one compact overlay for the held-out comparison: `4 CANDIDATES → RIDGE RERANKER → SELECTED CANDIDATE` and `+0.33% mean-NED vs strongest fixed · no exact-recovery gain`. | “Here is the machine-learning role: four transparent methods create candidates, and a small ridge reranker ranks them from read agreement and sequence features. It does not generate DNA. On a held-out synthetic split, it improved mean normalized edit distance by only zero point three three percent versus the strongest fixed method, with no exact-recovery gain.” |
| **1:42–1:57** | Cut to the separate blocked take. Show the 3-read, 0.050, seed-0 settings, then **Corruption detected**, **Output blocked**, and the absence of a download button. Do not display an unsupported recovery count in an overlay. | “Now I reduce the evidence to three reads and raise each error probability to five percent. Recovery fails, SHA-256 blocks the output, and no download appears. Detection is not error correction.” |
| **1:57–2:14** | Show a readable crop of the committed 48-file benchmark. Highlight only the `11 reads / 1% / 12 of 12` and `7 reads / 2% / 2 of 12` cells. Label the crop `SEPARATE CONSENSUS-ONLY SYNTHETIC BENCHMARK`. | “A separate consensus-only synthetic benchmark covers forty-eight files. At eleven reads and one-percent errors it recovered twelve of twelve; at seven reads and two percent, only two of twelve. These are controlled results, not wet-lab performance.” |
| **2:14–2:25** | Make a fast, clean cut between the README's Codex collaboration section and terminal crops showing `151 passed` plus clean lint. | “I built the codec, reconstruction pipeline, learned reranker, controls, and interface with Codex powered by GPT-5.6 Sol. The repository passes 151 tests.” |
| **2:25–2:40** | Return to the app, open **Scientific scope and production gaps**, and highlight the relevant lines. End on the hero and verification instrument, not the sandbox. | “The demo is capped at 256 bytes, with known routing and order, no ECC, and no wet-lab validation. Next, I would test a constraint-aware neural loss on real reads. Today, the controlled file-to-DNA-to-verified-file loop works.” |

## Editing notes

- Keep visual changes every 3–7 seconds while allowing the voice to remain calm. The target narration
  is approximately 340 words, or about 127 words per minute.
- Use only the two explanatory overlays described above. Everything else should be the deployed app,
  committed benchmark, README, or real test output.
- Record the success footage before changing settings for the blocked take. Reassemble the clips in
  the scripted order; do not try to perform both runs continuously.
- Preserve readable text. Use crop-and-zoom movement instead of shrinking the whole desktop.
- Do not show the **Strand sandbox** or optional GPT analyst; they are secondary to the file-recovery
  story.
- Use a subtle click sound only if it is original or licensed. Silence is preferable to stock music.
- Export at 1080p with H.264 video and AAC audio. Confirm the final cut is no longer than 2:45 and
  remains comfortably below the three-minute judging limit.

## Final compliance check

- [ ] Redesigned public deployment matches every screen shown.
- [ ] Successful default run and deterministic blocked run were freshly recorded.
- [ ] Clear English audio uses Álvaro's natural voice and stays near 125–130 words per minute.
- [ ] Archive purpose, exact ML role, benchmark scope, Codex contribution, and limitations are all
  stated aloud.
- [ ] No live-API claim, Strand sandbox, optional GPT analyst, secret, private notification,
  unlicensed music, or unrelated brand appears.
- [ ] New final cut is between 2:35 and 2:45 and the public video URL has been verified after upload.
