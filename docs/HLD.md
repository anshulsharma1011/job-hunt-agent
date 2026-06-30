# Job Hunt Agent — High Level Design

**Author:** Anshul Sharma
**Status:** Draft v2 — T1–T7, T20 implemented
**Last Updated:** 2026-06-30

---

## 1. Overview

An AI-powered, locally-run job hunting agent that autonomously discovers, scores, and ranks job opportunities against a structured user profile — and in later phases, drafts applications and outreach for human approval before anything leaves the system.

**Phase 1 goal:** Surface the right opportunities, ranked by fit, with zero outbound risk.
**Long-term goal:** End-to-end job hunt automation with a human-in-the-loop approval gate on every outbound action.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          CLI / Scheduler                             │
│              (manual trigger or APScheduler cron)                    │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR                                 │
│                    (LangGraph State Machine)                         │
│                                                                      │
│   load_profile → run_discovery_match → store_results → run_reporter  │
│                        │                                             │
│                    HOOK LAYER                                        │
│     (dedup · rate limiter · schema validator · source policy         │
│      · budget gate)                                                  │
└────────┬─────────────────────────────────┬────────────────┬──────────┘
         │                                 │                │
         ▼                                 ▼                ▼
┌─────────────────┐             ┌──────────────────┐  ┌────────────┐
│  Profile Agent  │             │ Discovery + Match │  │  Reporter  │
│                 │             │      Agent        │  │   Agent    │
│ PDF → structured│             │ Fetch → Score →  │  │            │
│ ProfileDoc +    │             │ Rank opportunities│  │ Writes     │
│ SearchCriteria  │             │ against profile   │  │ .txt report│
└─────────────────┘             └────────┬─────────┘  └────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │           ┌────────┴──────┐             │
                    ▼           ▼               ▼             ▼
             ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────┐
             │Greenhouse│ │  Adzuna  │ │  WeWorkRemot.│ │ RemoteOK │
             │REST API  │ │REST API  │ │     RSS      │ │ JSON API │
             └──────────┘ └──────────┘ └──────────────┘ └──────────┘
                    ▼           ▼               ▼
             ┌──────────┐ ┌──────────┐ ┌──────────────────────────────┐
             │ LinkedIn │ │  Indeed  │ │  Naukri (human-assisted)     │
             │ (jobspy) │ │ (jobspy) │ │  You paste HTML → agent reads│
             └──────────┘ └──────────┘ └──────────────────────────────┘
                                         │
                                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       SHARED CONTEXT STORE                           │
│                          (MongoDB local)                             │
│                                                                      │
│   profiles · opportunities · cycles · checkpoints                    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Components

### 3.1 CLI / Scheduler
- **CLI (Rich):** Manual trigger for a cycle, profile setup, viewing latest report.
- **Scheduler (APScheduler):** Runs cycles on a configurable cron (e.g. twice daily). Embedded in the process — no system cron needed.

### 3.2 Orchestrator (LangGraph)
The central coordinator. Owns the state machine and all transitions. No agent calls another agent directly.

- Built on **LangGraph StateGraph** with a typed `CycleState` shared across all nodes.
- **MongoDBSaver checkpointer** — crash mid-cycle resumes from last completed node, no work lost.
- Conditional routing: if no profile exists → trigger Profile Agent first; otherwise go straight to Discovery.
- All hook logic (dedup, rate limiting, schema validation, source policy, budget gate) lives here, not inside agents.

**Opportunity lifecycle states:**

```
discovered → scored → shortlisted / rejected
                           │              (Phase 2 onwards)
                           ▼
                    drafted → awaiting_approval → approved → sent → following_up → closed
```

### 3.3 Profile Agent
- Runs only when source materials change (not every cycle).
- Ingests: PDF resume (Phase 1), GitHub URL, personal website (later phases).
- Outputs: structured `ProfileDoc` (skills, experience, preferences, seniority) and a `SearchCriteria` spec (titles, locations, comp range, exclusions).
- Result versioned and stored in MongoDB; all other agents reference it by version ID.

### 3.4 Discovery + Match Agent
Combined into one agent for Phase 1 to reduce orchestration overhead.

- **Discovery:** Queries allowed job sources against `SearchCriteria`. Returns `RawOpportunity[]`.
- **Match:** Scores each opportunity against `ProfileDoc` using the local LLM. Returns `ScoredOpportunity[]` with score (0–100), fit rationale (3 bullets), red flags, and recommended track.
- Only opportunities above the configured score threshold (default: 70) are shortlisted.

### 3.5 Reporter Agent
- Read-only. Never triggers actions.
- Compiles cycle summary: discovered count, shortlisted count, top 10 matches with rationale, token spend, sources queried.
- Writes a `.txt` report to `output/` directory (Phase 1). JSON sidecar written alongside for Phase 3 learning ingestion.

### 3.6 Hook Layer
Interception points the orchestrator runs around agent actions. Enforced in code, not prompts.

| Hook | When it fires | What it does |
|------|--------------|--------------|
| Source Policy | Pre-fetch | Blocks disallowed sources; flags human-assisted ones |
| Rate Limiter | Pre-fetch | Caps requests per source per cycle |
| Budget Gate | Pre-agent | Hard-stops if token spend exceeds config limit |
| Schema Validator | Post-agent output | Rejects malformed output; triggers retry |
| Dedup | Post-discovery | Drops opportunity IDs already in the store |

---

## 4. Job Sources

| Source | Method | Policy | Notes |
|--------|--------|--------|-------|
| Greenhouse | Public REST API (per-company board) | Allowed | 154 verified company slugs in config |
| Adzuna | REST API (free tier) | Allowed | India endpoint; requires `ADZUNA_APP_ID` / `ADZUNA_API_KEY` |
| RemoteOK | JSON API | Allowed | No credentials; keyword filtering client-side |
| WeWorkRemotely | RSS feeds | Allowed | Feed categories configurable in YAML |
| LinkedIn | python-jobspy | Allowed | Mimics browser TLS fingerprint; no credentials needed |
| Indeed | python-jobspy | Allowed | `country_indeed=India` routes to `in.indeed.com` |
| Google Jobs | python-jobspy | Allowed (disabled) | Geo-restricted in India — currently returns 0 results |
| Naukri | Human-assisted | Human-assisted | You open browser, paste HTML — agent parses. Never automated. |

**Planned (post Phase 1):**
- **Glassdoor** (T21) — via python-jobspy; adds salary range data useful for scoring.
- **Greenhouse slug expansion** (T19) — move 1000+ slug candidates from config into MongoDB.

**Hard rules:**
- No headless browser automation (Playwright / Puppeteer / Selenium) on any source.
- No fake accounts. `robots.txt` respected on all sources.
- Naukri is permanently `human-assisted` — never promote to `allowed`.

---

## 5. LLM Layer

- **Phase 1:** Ollama running locally (`llama3.1:8b`) — zero cost, offline capable.
- **Phase 2+:** Swap to a cloud frontier model for draft quality.
- **Abstraction:** All agents call through a single `LLMClient` wrapper (LiteLLM). Switching models is a one-line config change with no agent code changes.

---

## 6. Shared Context Store (MongoDB)

Local MongoDB installed via Homebrew — no Docker, no VM overhead.

| Collection | Purpose |
|-----------|---------|
| `profiles` | Versioned ProfileDoc + SearchCriteria |
| `opportunities` | Every role seen, score, lifecycle state, history |
| `cycles` | Per-run metadata: counts, cost, duration, report path |
| `checkpoints` | LangGraph crash recovery (auto-managed) |

*Phase 2 adds:* `outreach_log`, `feedback`, `suppression`
*Phase 3 adds:* `learnings`

---

## 7. Technology Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Language | Python 3.12 | Best AI/agent ecosystem |
| Orchestration | LangGraph | Built-in state machine, checkpointing, parallelism |
| LLM (Phase 1) | Ollama `llama3.1:8b` | Free, local, good enough for scoring |
| LLM (Phase 2+) | Cloud frontier model via LiteLLM | Draft quality requires frontier model |
| LLM Abstraction | LiteLLM | Single interface across all LLM providers |
| Data Store | MongoDB (local Homebrew) | Document-native fit for nested job/profile data |
| Job scraping | python-jobspy | TLS-fingerprint scraping for LinkedIn, Indeed, Google Jobs |
| RSS parsing | feedparser | WeWorkRemotely RSS feeds |
| PDF Parsing | pdfplumber | Best for real-world resume layouts |
| CLI | Rich + questionary | Tables, color, interactive prompts |
| Scheduler | APScheduler | Embedded cron, no system dependencies |
| Config — Python | Per-source Pydantic models in `config/sources/` | One class per source, typed attribute access |
| Config — Data | Per-source YAML files in `config/yaml/sources/` | Data editable without touching Python |
| Secrets | `.env` (gitignored); python-dotenv | Credentials never in code or YAML |

---

## 8. Phased Delivery

### Phase 1 — Signal (Current)
**Goal:** Reliable, ranked job matches. No outbound.

- Profile Agent: PDF → ProfileDoc + SearchCriteria
- Discovery + Match Agent: fetch → score → rank
- Reporter: .txt digest per cycle
- Scheduler: automated runs
- CLI: manual trigger, profile setup, view report

**Done when:** Match quality is trusted enough to act on.

### Phase 2 — Draft + Approval
**Goal:** System proposes actions, human approves before anything sends.

- Draft Agent: tailored cover letters, application packages, outreach drafts
- Approval queue in CLI: batch review (approve / edit / reject)
- Send Executor: only component with outbound credentials; sandbox mode first
- Warm intro intelligence: surface 2nd-degree connection paths for human action
- Switch LLM to cloud frontier model for draft quality
- Adds: `outreach_log`, `feedback`, `suppression` collections

**Done when:** 10+ approvals sent with acceptable edit rate.

### Phase 3 — Learning + Follow-up
**Goal:** System improves from your feedback without prompt changes.

- Follow-up Agent: tracks sent items, drafts timed nudges through approval gate
- Learning distillation: feedback → compact rules → injected into agent context next cycle
- Reporter surfaces reply rates, outreach effectiveness trends
- Adds: `learnings` collection

---

## 9. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Orchestration model | Centralized (LangGraph) | 1 place for hooks, logging, approval — not peer-to-peer agent chatter |
| No outbound in Phase 1 | Hard constraint | Validate match quality before building anything that touches outside world |
| LLM abstraction via LiteLLM | Yes | Phase 1 Ollama, Phase 2 cloud — zero agent rewrites on swap |
| MongoDB over SQLite | MongoDB | Opportunities/profiles are nested documents, not flat rows |
| No Docker | Homebrew MongoDB | Docker VM overhead on macOS is unnecessary for a local tool |
| Naukri human-assisted | Permanent | No public API; headless scraping risks account ban — never automate |
| python-jobspy for LinkedIn/Indeed | Yes | RSS blocked; jobspy uses TLS fingerprinting to mimic a real browser without fake accounts |
| Per-source config models | Yes | `IndeedConfig` can carry `country` without polluting shared `JobSpyConfig` |
| Draft Agent has no send capability | Hard constraint | Sending is a separate gated step; agents structurally cannot send |

---

## 10. Open for Phase 2

- Email channel: own authenticated domain vs. provider (affects deliverability)
- Application tailoring depth: light resume highlights vs. full per-role variant
- Approval cadence: real-time per draft vs. batched once/twice daily
- Report delivery: .txt file (Phase 1) → email digest or web dashboard (Phase 2)
