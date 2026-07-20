# OpenAI Build Week Submission Checklist

> **Official deadline:** Tuesday, July 21, 2026 at **5:00 PM Pacific Time (PDT)** —
> Wednesday, July 22, 2026 at **2:00 AM Europe/Madrid (CEST)**. Registration and submission
> close at the same time. Submit early; the Official Rules and `openai.devpost.com` are the final
> source of truth.

Status key: `[x]` verified locally; `[ ]` still requires action or external confirmation.

## Eligibility and registration

- [ ] Confirm the entrant is at least the age of majority in their place of residence, or use an
  eligible parent/guardian where required.
- [ ] Confirm residence in an OpenAI API-supported country or territory and that no excluded
  jurisdiction, employment relationship, judging relationship, or conflict of interest applies.
- [ ] Confirm the project was not developed with prohibited financial or preferential support
  from OpenAI or Devpost.
- [ ] Create or sign in to the entrant's Devpost account.
- [ ] Click **Join Hackathon** at `openai.devpost.com` before registration closes.
- [ ] Confirm the entry is individual; if entering as a team or organization, appoint an eligible
  authorized representative and list every contributor accurately.
- [ ] Confirm the entrant has an OpenAI account and access to Codex. API access is needed only if
  the optional maintainer extension will be enabled.

## Project compliance

- [ ] Select the most defensible track. **Education** is the likely fit if the submission emphasizes
  the interactive scientific workbench and transparent teaching of DNA trace reconstruction.
- [x] A working local Streamlit application reconstructs controlled synthetic DNA traces and
  presents a coherent, English-language product experience.
- [x] GPT-5.6 Sol was used through Codex to develop and validate the Build Week extension.
- [x] The code includes a separate, optional Responses API analyst configured for `gpt-5.6` and
  covered by mocked integration tests.
- [ ] Do not advertise the optional analyst as live unless an actual call is completed and the
  entrant—not a judge—provides the deployed server-side key.
- [ ] Confirm the deployed project behaves exactly as shown in the video and described on Devpost.
- [x] Verify all third-party packages, data, fonts, images, and other assets are authorized and
  comply with their licenses; add attribution where appropriate.
- [ ] Confirm the submission is original, solely owned by the entrant/team, contains no secrets or
  personal data, and does not infringe copyright, trademark, patent, privacy, or other rights.
- [ ] Keep claims precise: this is controlled synthetic, uncoded reconstruction with
  inference-time biological constraints—not a neural training-loss result, CNR validation,
  TrellisBMA reproduction, or state-of-the-art claim.

### Required pre-existing-project disclosure

- [x] Add a clearly dated **Build Week work** section to the README. Distinguish the pre-hackathon
  simulator from the meaningful extension built during the Submission Period.
- [x] State that the earlier work comprised the categorical IDS simulator, its initial CLI/tests,
  and channel documentation.
- [x] State that Build Week added the end-to-end reconstruction pipeline, alignment-aware
  consensus, medoid and equal-budget search controls, biological constraints, benchmark artifacts,
  Streamlit product experience, GPT-5.6 Sol development through Codex, and an optional analyst.
- [ ] Back the distinction with dated commits, timestamped Codex session evidence, or equivalent.
  Only work added during the Submission Period will be evaluated.

## Repository and testing

- [x] MIT license is present.
- [x] Automated suite currently passes: **90 tests**.
- [x] Current Ruff quality checks pass.
- [x] The default experiment and Streamlit render path have been smoke-tested locally.
- [x] Run the exact documented install and start commands in a clean environment or fresh clone.
- [ ] Confirm a clean core install does not install the OpenAI SDK or require an API key. Test the
  optional analyst separately only if it will be advertised as live.
- [ ] Scan the entire repository and Git history for API keys, tokens, credentials, private paths,
  personal data, generated junk, and oversized files.
- [ ] Create an intentional Git history that preserves honest timing and clearly identifies Build
  Week additions.
- [ ] Create and push the final GitHub repository.
- [ ] Make the repository public, or share a private repository with both
  `testing@devpost.com` and `build-week-event@openai.com`.
- [ ] Confirm the repository URL works in a signed-out/incognito browser.
- [ ] Tag or record the exact commit submitted to Devpost.

## README and Codex evidence

- [x] Current application, code, tests, documentation, and repository text are in English.
- [x] Replace the outdated simulator-only README with the current HelixTrace product story.
- [x] Put a strong screenshot/result and concise value proposition at the top.
- [x] Document features, architecture, scientific scope, setup, launch command, testing command,
  the complete no-key workflow, and separate optional maintainer configuration.
- [x] Include exact judge testing instructions that do not require rebuilding the project from
  scratch beyond the documented install.
- [x] Add the required Codex collaboration section: what Codex accelerated, what the entrant
  decided, and how GPT-5.6 Sol contributed through Codex development.
- [x] Include the pre-existing versus Build Week disclosure described above.
- [x] Include limitations and an honest “What did not work / What comes next” section.
- [x] Add license and third-party attribution links.
- [ ] Run `/feedback` in the Codex project thread where most core functionality was built and save
  the resulting **Codex Session ID** for the submission form.

## Demonstration video

- [x] Write a script that fits comfortably under three minutes; judges need not watch beyond 3:00.
- [ ] Show the live product, not slides alone: generate noisy traces, compare reconstruction methods,
  isolate evidence-only versus biology-aware search, and generate the local guided interpretation
  without an account or API key.
- [ ] Explain clearly with audio what was built and how Codex powered by GPT-5.6 Sol was used during
  development; do not claim a live Responses API call.
- [ ] State the controlled-synthetic and inference-only limitations aloud or visibly.
- [ ] Avoid unlicensed music, third-party trademarks, and copyrighted material.
- [ ] Record at readable resolution with legible text and clean audio.
- [ ] Upload the final video to YouTube as **Public** and keep it publicly visible.
- [ ] Verify the full YouTube video and audio in a signed-out/incognito browser.
- [ ] Save the public YouTube URL for Devpost.

## Hosting and judge access

- [ ] Deploy a working, free-to-access demo and save its public URL.
- [ ] Confirm the deployed core app has no `OPENAI_API_KEY`, requires no OpenAI account or credits,
  and completes every advertised public workflow.
- [ ] If the optional analyst is later enabled, use an entrant-funded server-side secret and never
  commit or display it; do not ask judges to provide a key.
- [ ] Confirm judges can use the core demo without sign-in, payment, geographic restriction, or a
  test account. If access is private, provide working credentials in the testing instructions.
- [ ] Confirm the hosted app starts reliably after sleeping and presents the optional integration as
  unavailable—not broken—when no maintainer key is configured.
- [ ] Keep the project free and unrestricted for judging through **August 5, 2026 at 5:00 PM PT**
  (August 6 at 2:00 AM Europe/Madrid).
- [ ] Confirm the deployed URL, repository URL, and YouTube URL all work from a clean browser.

## Devpost form

- [ ] Create the submission draft before the deadline.
- [ ] Enter the final project title and select the correct category.
- [ ] Write an English description covering the real audience, problem, features, technical
  implementation, Codex/GPT-5.6 Sol development workflow, optional API role, impact, novelty, and
  limitations.
- [ ] Address all four equally weighted judging dimensions: technological implementation, design,
  potential impact, and quality of the idea.
- [ ] Add clear screenshots or project images that match the final app.
- [ ] Add the public repository URL, deployed demo URL, and public YouTube URL.
- [ ] Add concise testing instructions and any credentials if genuinely required.
- [ ] Add the required `/feedback` Codex Session ID.
- [ ] List every team member/contributor accurately and confirm ownership.
- [ ] Review every field in English and confirm all statements match the repository, video, and app.
- [ ] Submit the entry; saving a draft is not a final submission.

## Final verification

- [ ] Run tests and lint once more against the exact final commit.
- [ ] Reinstall and launch from the README instructions using the exact final repository.
- [ ] Test the public app's default reconstruction, parameter controls, validation, comparison
  metrics, free guided interpretation, and no-key completion path. Test a live analyst only if it is
  explicitly enabled.
- [ ] Open the repository, hosted demo, and YouTube video from a signed-out/incognito browser.
- [ ] Confirm there are no secrets, broken links, inaccurate claims, stale screenshots, or private
  resources in any submission material.
- [ ] Confirm the Build Week disclosure and dated Codex/commit evidence are visible to judges.
- [ ] Confirm the Devpost entry shows **Submitted**, not Draft, before the deadline.
- [ ] Save screenshots or confirmation emails proving successful submission and the submitted URLs.
- [ ] Do not rely on last-minute uploads; no substantive changes are permitted after the Submission
  Period unless OpenAI/Devpost expressly allows a limited correction.
