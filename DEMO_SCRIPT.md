# HelixTrace demo video

**Target length:** 2:10–2:25<br>
**Audio:** Álvaro's natural voice; no synthetic narration and no copyrighted music<br>
**Visual style:** real product interaction, visible cursor, short zooms, almost no title cards

## Recording setup

- Open the public app in **File recovery** mode at 1920×1080.
- Leave the built-in `proof.txt` selected, with the learned reranker, 11 reads, 0.010 error,
  and seed 43.
- Keep the local README and a clean terminal crop of the passing checks ready off-screen.
- Record one continuous product flow, then remove waits and add gentle crop/zoom motion in editing.
- Do not show API keys, personal notifications, browser bookmarks, or unrelated tabs.

## Timed shot list and narration

| Time | What the viewer sees | Álvaro says |
|---|---|---|
| **0:00–0:08** | Cold open: cursor moves from `proof.txt` to **Encode, simulate & recover**. Do not begin with a static logo card. | “What if a file could survive being converted into DNA, copied with errors, and read back correctly?” |
| **0:08–0:20** | Quick zoom across the hero pills: constrained code, learned reranker, cryptographic verification. | “This is HelixTrace. It takes real bytes, encodes them as synthesis-aware DNA fragments, reconstructs noisy reads, and only returns a file if its hash is correct.” |
| **0:20–0:31** | Click **Encode, simulate & recover**. Keep the cursor visible; compress the processing wait in the edit. | “I am using the learned decoder, eleven reads per fragment, and one percent each for insertion, deletion, and substitution errors.” |
| **0:31–0:48** | Scroll through the five moving stages and KPIs: 5 bytes, 848 nt, 22/22 fragments, 242 reads. | “The file becomes a versioned frame with SHA-256, then a reversible one-bit-per-nucleotide code. It guarantees exactly fifty percent GC and no adjacent repeated bases.” |
| **0:48–1:02** | Land on **Exact file recovered**, the hash, and the enabled download button. Briefly click or hover the download button; do not open a file picker. | “Every fragment was reconstructed from the noisy clusters, the decoded bytes matched the embedded digest, and only then did HelixTrace enable the download.” |
| **1:02–1:18** | Select **Fragment 4**, then zoom between synthetic ground truth, its 41-base noisy read, and the recovered 40-base sequence. | “Here is the actual evidence. The middle read contains an extra base, while the recovered fragment matches the hidden source. The reconstruction function never receives that source or the expected hash.” |
| **1:18–1:36** | Show the learned-selector caption, then a clean crop of the held-out metrics in the README. | “The machine-learning component is a small ridge reranker trained on eighty synthetic experiments and tested on a separate one-hundred-twenty experiment seed split. It reduced mean normalized edit distance by eleven point six percent versus consensus, but only zero point three three percent versus the strongest fixed method, with no exact-recovery gain. I report that small result honestly.” |
| **1:36–1:50** | Fast cut to the file benchmark table: 11 reads/1% = 12/12; 7 reads/2% = 2/12. | “The end-to-end benchmark shows the expected reliability curve: twelve of twelve files recovered at eleven reads and one percent errors, but only two of twelve at seven reads and two percent errors.” |
| **1:50–2:06** | Switch to the local README repository map, then a clean terminal crop showing `151 passed` and the lint result. Keep browser chrome and third-party logos out of frame. | “I built this with Codex powered by GPT-5.6 Sol. Codex helped me turn my research notes into the architecture, implement the codec and reconstruction pipeline, train the reranker, challenge the scientific claims, and verify one hundred fifty-one tests and the live interface.” |
| **2:06–2:22** | Return to the app and open **Scientific scope and production gaps**. End on the product hero. | “This is still a controlled synthetic prototype: clusters and fragment order are known, and it has no wet-lab validation or error-correcting code. The next step is real nanopore data and a neural reconstructor. But today, HelixTrace already completes the full file-to-DNA-to-file loop.” |

## Editing notes

- Keep cuts every 3–7 seconds, driven by cursor movement or a result changing on screen.
- Use only two minimal overlays: `FILE → DNA → NOISY READS → VERIFIED FILE` and the held-out
  comparison. Everything else should be the real app or repository.
- Speed up the six-second learned run rather than covering it with a presentation slide.
- Preserve readable text; zoom into one area instead of shrinking the whole desktop.
- Use a subtle click sound only if it is original or licensed. Silence is preferable to stock music.
- Export at 1080p, H.264 video + AAC audio, and verify the final duration is below three minutes.

## Final compliance check

- [ ] Public YouTube visibility.
- [ ] Clear audio in English with Álvaro's own voice.
- [ ] Real demo matches the deployed build.
- [ ] Codex and GPT-5.6 use explained aloud.
- [ ] No third-party music, trademarks used as decoration, secrets, or personal notifications.
- [ ] Final video remains under three minutes.
