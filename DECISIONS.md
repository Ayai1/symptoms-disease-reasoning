# Decision Log

Each entry records a decision, the reasoning behind it, and its consequences. Entries are not edited after acceptance; a later entry supersedes an earlier one by referencing its ID.

Format: **ID — title** · date · status

---

## D-001 — Replace the legacy dataset with DDXPlus
2026-10-09 · accepted

**Decision.** Train and evaluate on DDXPlus (49 conditions, ~1.3M synthetic patients, 223 evidence items). The legacy Kaggle CSV is retired as a training source.

**Reasoning.** The legacy CSV has 304 unique rows out of 4,920; 100% of test rows in the original random split are exact copies of training rows, so any reported accuracy is leakage (measured in `docs/PLAN.md` §1.1). DDXPlus is large enough for a held-out evaluation and a separate calibration split, records negative and categorical evidence needed for adaptive questioning, provides an initial complaint per patient for interview simulation, and is released under CC-BY.

**Consequences.**
- The README must state plainly that DDXPlus is **synthetic** (generated from a proprietary knowledge base by a rule-based system) and that its 49 conditions are **mostly respiratory, cardiac and ENT**. All metrics are reported as metrics on that synthetic, scoped benchmark, not as clinical accuracy.
- Conditions in the legacy set that DDXPlus does not cover (e.g. dermatological, hepatic, urinary) are out of scope. The assistant states its scope when input does not match.
- Identical evidence sets across DDXPlus splits are deduplicated before evaluation, and both official-split and deduplicated metrics are reported.

## D-002 — Emergency and support resources: India, US, UK
2026-10-09 · accepted

**Decision.**
- Launch regions: India (`IN`), United States (`US`), United Kingdom (`GB`, labelled "United Kingdom").
- The frontend prefills the region from the browser locale; the user confirms or changes it. If the locale gives no supported region, the default is India.
- If the user selects "Other / not listed", only a generic "call your local emergency number" message is shown, with no numbers.
- All numbers live in one file, `backend/app/safety/data/emergency_resources.yaml`, with a `last_verified` date and a source URL for every number.

**Reasoning.** One source of truth prevents numbers drifting between backend and frontend. A per-number source makes re-verification mechanical.

**Re-verification.** The original request was for an LLM to re-verify the numbers at build time. That part is adjusted:
- An LLM call inside the build makes builds non-deterministic, requires an API key and network access in CI, and can return a confident wrong answer. That conflicts with D-005 (no LLM in the safety path) and D-007 (reproducible builds).
- Instead, CI runs a deterministic gate (`backend/scripts/check_emergency_resources.py`) that fails when `last_verified` is older than 90 days or when any entry lacks a source. A failing gate forces a re-verification pass, done by a person or by an assistant session with web access, against the listed official sources, followed by a date bump in the same commit.
- Verification on 2026-10-09 was done through web search results restricted to official domains (pib.gov.in, mohfw.gov.in, 988lifeline.org, samhsa.gov, poisonhelp.hrsa.gov, nhs.uk). The official pages themselves were not reachable from the build environment; the YAML records this as `verification_method`.

## D-003 — Show likelihood bands by default
2026-10-09 · accepted

**Decision.** Hypotheses are shown as bands (low / moderate / higher) with relative ordering. Calibrated numeric probabilities appear only in an expandable detail panel, together with the reliability plot.

**Reasoning.** Calibration holds for the synthetic DDXPlus population, not for an individual user. A bare percentage is easily read as personal risk.

## D-004 — Interview strategy: expected information gain
2026-10-09 · accepted

**Decision.** The legacy "Tree-of-Thoughts" heuristic is replaced by question selection on expected information gain over the calibrated posterior, with an explicit stopping rule and abstention. Code and docs call it "hypothesis-driven questioning".

**Reasoning.** The legacy component is a heuristic ranker with an arithmetic score capped at 0.9 (the source of the "90% confidence" output), not a tree search. EIG is measurable and testable.

## D-005 — LLM adapter: built in Phase 5, off by default, never in the safety path
2026-10-09 · accepted

**Decision.**
- A provider-agnostic `LLMClient` interface with one concrete implementation for a provider for which a key is available.
- Disabled by default. The application works fully without any key.
- The LLM is never used for red-flag detection, medication refusal, emergency resources, probabilities or question selection. Safety code has no import path to the LLM package; a test enforces this.

## D-006 — Explanations from MedlinePlus/CDC; PubMed not shipped
2026-10-09 · accepted

**Decision.** User-facing explanations come only from a small, pinned corpus of public-domain MedlinePlus health-topic summaries (and CDC pages where needed). A.D.A.M. and ASHP content are excluded. PubMed abstracts and RxNorm drug-name extraction are removed.

**Reasoning.** Licensing (PubMed abstracts are publisher-copyrighted; full RxNorm requires a UMLS licence), audience fit, and medication-safety concerns.

## D-007 — Model artifacts via GitHub Releases, checksum-verified
2026-10-09 · accepted

**Decision.** Trained artifacts are published as GitHub Release assets. Docker builds download a pinned release and verify SHA-256 checksums stored in the repository; a mismatch fails the build. The training pipeline stays in the repository so artifacts can be regenerated.

**Reasoning.** Fast, reproducible builds without downloading the DDXPlus archive or training during image builds.

## D-008 — Hosting: Hugging Face Spaces (backend) + Vercel (frontend)
2026-10-09 · accepted

**Decision.** Backend on a Hugging Face Docker Space (free CPU), frontend on Vercel (free tier).

**Consequences.**
- CORS: the backend allows only origins listed in `APP_CORS_ORIGINS`; no credentials; methods `GET, POST, DELETE`.
- Cold starts: both hosts sleep when idle. The frontend polls `GET /api/v1/health` on load and shows a "starting the server" state until it reports ready. Cold-start behaviour is documented in the deployment guide.
- Startup check: the backend loads and validates safety rules and emergency resources during startup and refuses to start if either is invalid. `GET /api/v1/health` reports per-component status and returns 503 if a required component is missing. The Docker image adds a `HEALTHCHECK` against that endpoint (Phase 8).

## D-009 — Keep `legacy/` until Phase 8
2026-10-09 · accepted

**Decision.** The prototype is moved unchanged to `legacy/` in Phase 1 and deleted in Phase 8. Git history preserves it.

## D-010 — Licence: MIT, with NOTICE attributions
2026-10-09 · accepted

**Decision.** Repository licensed under MIT. `NOTICE` carries attributions for DDXPlus (CC-BY) and MedlinePlus (U.S. National Library of Medicine).

**Open detail.** The exact CC-BY version of DDXPlus is to be confirmed from the figshare record in Phase 2 (figshare was not reachable from the build environment on 2026-10-09).

## D-011 — Session lock after a red flag, with a way forward
2026-10-09 · accepted

**Decision.**
- When a red-flag rule fires, the session is locked: no further symptom analysis in that session.
- The response always includes a "Start a new session" action, so the screen is not a dead end.
- Self-harm flags show crisis-support resources first and prominently (with the emergency number), in supportive wording, rather than a lock message.

## D-012 — Runtime versions
2026-10-09 · accepted

**Decision.** Python 3.12. Node.js 24 (Active LTS on 2026-10-09; end of life 2028-04-30).

**Reasoning.** Node 20 reached end of life in April 2026. Per the Node.js release schedule (`nodejs/Release/schedule.json`), Node 22 is in maintenance (end of life 2027-04-30), Node 24 is Active LTS until 2026-10-20, then maintenance until 2028-04-30, and Node 26 becomes Active LTS on 2026-10-28.

**Follow-up.** At the start of Phase 7 (frontend), re-check the schedule. If Node 26 has reached Active LTS, move to Node 26 and record a superseding entry.

## D-013 — Package managers: uv and pnpm
2026-10-09 · accepted

**Decision.** `uv` (with a committed `uv.lock`) for Python; `pnpm` (with a committed `pnpm-lock.yaml`) for the frontend. CI installs from lockfiles only (`uv sync --frozen`, `pnpm install --frozen-lockfile`).

## D-014 — Red-flag detection on accumulated signals, not stored text
2026-10-09 · accepted

**Decision.** Red-flag patterns map message text to named *signals* (e.g. `chest_pain`, `breathlessness`). Rules are combinations of signals. The session keeps only the set of signal IDs seen so far, never the text, so combinations split across messages ("chest pain" then "can't breathe") still fire without retaining user text.

**Reasoning.** Meets the privacy constraint (no message text retained) while catching multi-turn presentations.

## D-015 — Phase 1 exposes a safety-only message endpoint
2026-10-09 · accepted

**Decision.** Phase 1 ships `POST /api/v1/sessions/{id}/messages` returning JSON. It runs the safety gate only; non-flagged messages receive a notice that symptom analysis is not yet available. SSE streaming and the reasoning engine arrive in Phases 3–6.

**Reasoning.** Lets the red-flag bypass, session lock, logging privacy and rate limits be tested end to end before any model exists.
