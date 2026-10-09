# Symptom Assistant

An educational, chat-style assistant that takes a free-text description of symptoms, asks follow-up questions, and lists possible matching conditions with calibrated uncertainty and cited explanations. It is not a medical device and does not diagnose.

> **Data and scope.** The model is trained and evaluated on [DDXPlus](https://arxiv.org/abs/2205.09148), a **synthetic** dataset: its patients were generated from a proprietary medical knowledge base by a rule-based system, not collected from real patients. Its 49 conditions are **mostly respiratory, cardiac, and ear, nose and throat (ENT) conditions**. All reported metrics describe performance on this synthetic, narrowly scoped benchmark. They do not measure clinical accuracy, and conditions outside this scope are not covered.

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Audit and plan (`docs/PLAN.md`) | Done |
| 1 | Backend foundations, safety gate, CI | Done |
| 2 | DDXPlus data pipeline, model, calibration, evaluation | Not started |
| 3 | Reasoning engine (information-gain questioning, stopping rule) | Not started |
| 4 | Free-text symptom extraction | Not started |
| 5 | Retrieval corpus, grounded explanations, optional LLM adapter | Not started |
| 6 | Streaming API | Not started |
| 7 | Next.js frontend | Not started |
| 8 | Docker, deployment, documentation | Not started |

The current backend runs the safety gate only. Messages without warning signs receive a notice that symptom analysis is not yet available. No model metrics exist yet; this section will list measured results from `backend/reports/metrics.json` once Phase 2 is complete.

## Safety behaviour

- **Red flags.** Every message is checked by deterministic rules before anything else (`backend/app/safety/data/red_flags.yaml`). Examples: chest pain with breathlessness, stroke signs, severe breathing difficulty, severe allergic reaction, severe bleeding, seizure, meningitis signs, fever in a baby, pregnancy warning signs, poisoning, and self-harm. A match returns emergency guidance and locks the session; the response always offers a "start a new session" action. Self-harm matches show crisis-support contacts first.
- **Signals across messages.** Findings are combined across the conversation (for example, "chest pain" in one message and "sweating" in the next). Only signal identifiers are kept, never message text.
- **Urgent notices.** Some findings (for example, chest pain alone or coughing up blood) produce a "get medical advice today" notice without locking the session.
- **Medication requests.** Questions about medicines, doses or treatments are declined and redirected to a pharmacist or doctor.
- **Emergency contacts.** India (default), United States and United Kingdom, in one file (`backend/app/safety/data/emergency_resources.yaml`) with a `last_verified` date and a source for every number. CI fails if the date is more than 90 days old. Other regions receive a generic "call your local emergency number" message.
- **No LLM in the safety path.** Safety code has no dependency on models or language models; a test enforces this.

## Privacy

- No accounts and no database. Sessions live in memory and expire after 30 minutes idle or 2 hours in total; `DELETE /api/v1/sessions/{id}` erases one immediately.
- Message text is checked and then discarded. It is not stored in the session and is never logged.
- Logs are JSON with an allowlist of fields: request ID, route template, status, latency, outcome, rule IDs and a salted hash of the session ID. Client IP addresses are used in memory for rate limiting only.

## API (current)

Base path `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Component status; 503 if a required component is unavailable |
| GET | `/meta` | Disclaimer, supported regions, default region, scope note |
| GET | `/emergency-resources/{IN\|US\|GB\|OTHER}` | Contacts for a region |
| POST | `/sessions` | Create a session (`acknowledged_disclaimer: true` required) |
| GET | `/sessions/{id}` | Session status |
| DELETE | `/sessions/{id}` | Erase a session |
| POST | `/sessions/{id}/messages` | Send a message; returns a safety turn result |

Interactive documentation is served at `/api/v1/docs` outside production.

## Running locally

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync
uv run uvicorn app.main:create_app --factory --no-access-log --reload
```

Checks (the same steps CI runs):

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
uv run python scripts/check_emergency_resources.py
```

### Configuration

Environment variables use the `APP_` prefix (see `backend/app/config.py`).

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENVIRONMENT` | `development` | `production` disables the OpenAPI docs |
| `APP_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated list of allowed origins; `*` is rejected |
| `APP_TRUST_FORWARDED_FOR` | `false` | Use `X-Forwarded-For` for rate limiting behind a trusted proxy |
| `APP_SESSION_IDLE_TTL_SECONDS` | `1800` | Idle session expiry |
| `APP_SESSION_ABSOLUTE_TTL_SECONDS` | `7200` | Absolute session expiry |
| `APP_RATE_LIMIT_TURNS_PER_MINUTE` | `30` | Messages per client per minute |
| `APP_RATE_LIMIT_SESSIONS_PER_MINUTE` | `5` | New sessions per client per minute |
| `APP_MAX_BODY_BYTES` | `16384` | Maximum request body size |
| `APP_LOG_LEVEL` | `INFO` | Log level |

## Repository layout

```
backend/            FastAPI service, safety gate, tests
  app/safety/data/  Red-flag rules, medication guard, emergency contacts
  tests/safety/     Case suites for red flags and the medication guard
docs/PLAN.md        Audit, architecture, evaluation and safety plans
DECISIONS.md        Decision log
legacy/             Original prototype, kept for reference until Phase 8
```

## Licence

MIT (see `LICENSE`). Third-party data attributions are in `NOTICE`.
