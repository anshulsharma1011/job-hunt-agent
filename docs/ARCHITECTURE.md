# Job Hunt Agent — System Architecture

**Author:** Anshul Sharma
**Status:** Draft v2 — T1–T7, T20 implemented
**Last updated:** 2026-06-30

A locally-run, India-first agent system that finds, scores, and ranks job opportunities against a structured user profile — and in later phases, drafts applications and outreach for human approval before anything leaves the system. Coordinated by a LangGraph state machine, backed by a local MongoDB store, and powered by a local LLM via Ollama.

---

## 1. Design Principles

1. **One agent, one job.** Each agent owns a single specialized task. Agents never call each other directly — all work is handed back to the orchestrator.
2. **The orchestrator is the only coordinator.** No peer-to-peer agent chatter. All routing, sequencing, and state transitions flow through LangGraph. One place to insert hooks, logging, and approval.
3. **Nothing irreversible without a human.** Discovery, matching, and scoring run autonomously. Anything that touches the outside world — submitting an application, sending an email — stops at an approval gate. Phase 1 has no outbound at all.
4. **Guardrails are enforced in code, not in prompts.** Hooks sit between the agent's intent and the actual side effect. A prompt can be talked out of a rule; a hook cannot.
5. **Context compounds.** Every cycle writes structured results back to MongoDB. The system's judgment improves with use rather than starting cold each time.
6. **Build outbound last.** Phase 1 is fully read-only. Validate match quality before building anything that touches the outside world.
7. **LLM is a swappable dependency.** All agents call through a single LiteLLM wrapper. Phase 1 uses local Ollama (`llama3.1:8b`). Phase 2 switches to a cloud model for draft quality — one config change, zero agent rewrites.

---

## 2. System at a Glance

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLI / Scheduler                               │
│              (manual trigger  or  APScheduler cron)                  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                                  │
│                   (LangGraph StateGraph)                             │
│                                                                      │
│  load_profile ──► run_discovery_match ──► store_results ──► reporter │
│                         │                                            │
│                     HOOK LAYER                                       │
│            (dedup · rate limiter · schema validator                  │
│             source policy · budget gate)                             │
└──────┬───────────────────────────────────────────┬───────────────────┘
       │                                           │
       ▼                                           ▼
┌─────────────────┐                  ┌─────────────────────────────┐
│  Profile Agent  │                  │   Discovery + Match Agent   │
│                 │                  │                             │
│  PDF resume     │                  │  Greenhouse API             │
│       ↓         │                  │  Adzuna REST API            │
│  ProfileDoc +   │                  │  RemoteOK JSON API          │
│  SearchCriteria │                  │  WeWorkRemotely RSS         │
└─────────────────┘                  │  LinkedIn (jobspy)          │
                                     │  Indeed (jobspy)            │
                                     │  Naukri (human-assisted)    │
                                     │       ↓                     │
                                     │  Score + rank vs profile    │
                                     │  ScoredOpportunity[]        │
                                     └─────────────────────────────┘
                                                  │
                                                  ▼
                               ┌──────────────────────────────────┐
                               │         Reporter Agent           │
                               │  Read-only. Writes .txt report   │
                               │  to output/ — never triggers     │
                               │  any action.                     │
                               └──────────────────────────────────┘
                                                  │
                                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      SHARED CONTEXT STORE                            │
│                       (MongoDB — local)                              │
│                                                                      │
│   profiles · opportunities · cycles · checkpoints                    │
│   + outreach_log · feedback · learnings  (Phase 2 / 3)              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Roster

Each agent is a pure function: `(state slice, context) → updated state`. No agent sends anything to the outside world directly.

| # | Agent | Responsibility | Consumes | Produces |
|---|-------|---------------|----------|----------|
| 1 | **Profile Agent** | Parse resume → structured profile + search criteria | PDF resume | `ProfileDoc`, `SearchCriteria` |
| 2 | **Discovery + Match Agent** | Fetch opportunities from sources, score and rank against profile in one pass | `SearchCriteria`, `ProfileDoc` | `ScoredOpportunity[]` |
| 3 | **Draft Agent** *(Phase 2)* | Produce a tailored application package or outreach email draft depending on track | `ScoredOpportunity`, `ProfileDoc` | `DraftApplication` or `DraftEmail` — always `requires_approval: true` |
| 4 | **Reporter Agent** | Compile cycle summary into a report | All context writes since last report | `.txt` report file (Phase 1), email digest (Phase 2+) |

**Why 4 agents instead of the original 8:**
- Discovery and Match are combined — scoring in the same pass reduces orchestration overhead and latency for Phase 1.
- Contact Agent folded into Draft Agent context (warm intro paths surfaced as intelligence, not as a separate scraping step).
- Follow-up Agent deferred to Phase 3 — it requires outreach data that doesn't exist yet.

**Phase 1 boundary:** Profile Agent + Discovery+Match Agent + Reporter Agent only. Draft Agent does not exist in Phase 1.

---

## 4. The Orchestrator

Built on **LangGraph StateGraph**. Owns all state transitions — no agent advances state directly.

**What it does:**
1. **Owns the state machine.** One typed `CycleState` object flows through all nodes. Only the orchestrator writes lifecycle transitions.
2. **Routes between agents.** Declarative conditional edges — e.g., if no profile exists in MongoDB, route to Profile Agent first; otherwise skip straight to Discovery+Match.
3. **Crash recovery via checkpointing.** LangGraph's `MongoDBSaver` checkpoints state after each node. A crash mid-cycle resumes from the last completed node — no work is lost, no double-sends.
4. **Runs the hook layer.** Dedup, rate limiting, schema validation, budget gate — all enforced around agent calls, not inside them.
5. **Manages the approval queue** *(Phase 2).* Artifacts with `requires_approval: true` park in `awaiting_approval` state. On your decision, the orchestrator resumes or discards.

**Opportunity lifecycle:**
```
discovered → scored → shortlisted / rejected
                           │          (Phase 2+)
                           ▼
                  drafted → awaiting_approval → approved → sent → following_up → closed
```

---

## 5. Job Sources

| Source | Method | Policy | Notes |
|--------|--------|--------|-------|
| Greenhouse | Public REST API (per-company board) | Allowed | 154 verified company slugs; slug list in `config/yaml/sources/greenhouse.yaml` |
| Adzuna | REST API (free tier) | Allowed | India endpoint; credentials via `ADZUNA_APP_ID` / `ADZUNA_API_KEY` env vars |
| RemoteOK | JSON API | Allowed | No credentials; client-side keyword filtering |
| WeWorkRemotely | RSS feeds | Allowed | Feed categories configurable via `config/yaml/sources/weworkremotely.yaml` |
| LinkedIn | python-jobspy | Allowed | Mimics browser TLS fingerprint; no credentials needed |
| Indeed | python-jobspy | Allowed | `country_indeed=India` for regional endpoint; no credentials needed |
| Google Jobs | python-jobspy | Allowed (disabled) | Geo-restricted in India — returns 0 results; re-enable when jobspy fixes regional support |
| Naukri | Human-assisted | Human-assisted | You open browser, paste HTML — agent parses. Never automated. |

**Planned (post Phase 1):**
- **Glassdoor** (T21) — via python-jobspy; adds salary range data (`min_amount`, `max_amount`) useful for scoring.
- **Greenhouse slug expansion** (T19) — move 1000+ slug candidates from config into MongoDB `greenhouse_slugs` collection.

**Hard rules enforced by source-policy hook:**
- No headless browser automation (Playwright / Puppeteer / Selenium) on any source.
- No fake accounts.
- `robots.txt` respected on all sources.
- Naukri is permanently `human-assisted` — never promote to `allowed`.
- Source policy table lives in `config/yaml/sources/` — the hook reads it before every fetch.

---

## 6. Config Layer

All configuration lives under `config/` (Python models) and `config/yaml/` (data files). Python and YAML are intentionally separated so data files can be edited without touching code.

```
config/
  app_config.py            ← AppConfig root aggregate
  app_section.py           ← AppSection (name, env)
  llm_config.py            ← LLMConfig
  matching_config.py       ← MatchingConfig
  mongo_config.py          ← MongoConfig
  output_config.py         ← OutputConfig
  scheduler_config.py      ← SchedulerConfig
  loader.py                ← reads yaml/, applies env var overrides
  sources/
    base.py                ← SourcePolicyBase (policy, enabled)
    jobspy_config.py       ← JobSpyConfig (max_results, hours_old) — shared by LinkedIn, Indeed, Google
    indeed_config.py       ← IndeedConfig extends JobSpyConfig (+ country)
    greenhouse_config.py   ← GreenhouseConfig (companies list, max_per_run)
    adzuna_config.py       ← AdzunaConfig (app_id, api_key, location, max_per_run)
    remoteok_config.py     ← RemoteOKConfig
    weworkremotely_config.py ← WeWorkRemotelyConfig (categories list)
    naukri_config.py       ← NaukriConfig
    sources_config.py      ← SourcesConfig aggregate (named fields, one per source)
  yaml/
    app.yaml · llm.yaml · matching.yaml · mongodb.yaml · output.yaml · scheduler.yaml
    sources/
      greenhouse.yaml · adzuna.yaml · remoteok.yaml · weworkremotely.yaml
      linkedin.yaml · indeed.yaml · google.yaml · naukri.yaml
```

Sources are accessed as typed attributes (`config.sources.greenhouse`, `config.sources.adzuna`, etc.) — no dict lookups, no Optional guards.

---

## 7. Compliance

**Target geography: India-first.** India has no CAN-SPAM equivalent. The DPDPA 2023 applies to processing Indian residents' personal data — keep scraped contact data minimal and purposeful.

**US/EU recipients:** If any source returns roles at US or EU-headquartered companies, those go into a separate bucket. CAN-SPAM applies to emails sent to US recipients regardless of sender location. GDPR applies to EU recipients. Phase 2 will gate these behind an additional flag before the Draft Agent processes them.

**Scraping:** Only sanctioned APIs and structured feeds are automated. python-jobspy is used for LinkedIn and Indeed — it targets public job listing pages without fake accounts or headless browsers. Naukri is human-assisted (see Section 5).

---

## 8. Hook Layer

Hooks are interception points the orchestrator runs around agent actions.

| Hook | Fires | Action |
|------|-------|--------|
| Source policy | Pre-fetch | Blocks disallowed sources; flags human-assisted ones |
| Rate limiter | Pre-fetch | Caps requests per source per cycle — hard stop |
| Budget gate | Pre-agent | Stops cycle if token spend exceeds config limit |
| Schema validator | Post-agent output | Rejects malformed output; triggers retry with backoff |
| Dedup | Post-discovery | Drops opportunity IDs already in MongoDB |
| Approval gate *(Phase 2)* | Post-draft | Parks `requires_approval: true` artifacts; surfaces to CLI queue |

**Kill switches:**
- Global pause flag — stops all outbound instantly.
- Per-source circuit breaker — too many fetch failures → back off that source for the rest of the cycle.

---

## 9. Shared Context Store

Local **MongoDB** installed via Homebrew. No Docker, no VM overhead.

| Collection | Holds | Added in |
|-----------|-------|----------|
| `profiles` | Versioned `ProfileDoc` + `SearchCriteria` | Phase 1 |
| `opportunities` | Every role seen, score, rationale, lifecycle state, history | Phase 1 |
| `cycles` | Per-run metadata: counts, token spend, duration, report path | Phase 1 |
| `checkpoints` | LangGraph crash-recovery state (auto-managed) | Phase 1 |
| `outreach_log` | Drafts, approval decisions, sends, reply signals | Phase 2 |
| `suppression` | Do-not-contact list, opted-out contacts | Phase 2 |
| `feedback` | Approve/edit/reject decisions + diffs of your edits | Phase 2 |
| `learnings` | Distilled per-agent rules injected into prompts next cycle | Phase 3 |
| `greenhouse_slugs` | Verified Greenhouse company slugs (T19 enhancement) | Post Phase 1 |

**How learning works (Phase 3, no model training required):**
1. Every approval-gate decision captured as structured feedback (approved / approved-with-edits / rejected + reason).
2. A nightly distillation job turns raw feedback into compact rules in `learnings`.
3. Rules injected into the relevant agent's context on next cycle. Scoped per-agent — Match Agent learnings never pollute Draft Agent context.

---

## 10. End-to-End Flow (Phase 1 Cycle)

1. **Trigger.** CLI command or APScheduler cron fires the LangGraph graph.
2. **Load profile.** Orchestrator reads active `ProfileDoc` from MongoDB. If none exists, routes to Profile Agent first.
3. **Profile Agent** *(if needed).* Parses PDF resume → produces `ProfileDoc` + `SearchCriteria`. Stored in MongoDB, versioned.
4. **Discovery + Match Agent.** Queries allowed sources against `SearchCriteria`. Dedup hook drops known opportunity IDs. LLM scores each against `ProfileDoc` — score 0–100, fit rationale (3 bullets), red flags, recommended track. Opportunities below threshold archived as `rejected`; above threshold stored as `shortlisted`.
5. **Store results.** Orchestrator writes all `ScoredOpportunity[]` to `opportunities` collection. Updates `cycles` record.
6. **Reporter Agent.** Reads cycle data from MongoDB. Writes `.txt` report to `output/` directory: top matches with rationale, counts, token spend.

---

## 11. Technology Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.12 |
| Orchestration | LangGraph (StateGraph + MongoDBSaver checkpointer) |
| LLM — Phase 1 | Ollama `llama3.1:8b` (local, free) |
| LLM — Phase 2+ | Cloud frontier model via LiteLLM |
| LLM abstraction | LiteLLM (swap model via config, zero agent changes) |
| Data store | MongoDB (local, Homebrew — no Docker) |
| Job scraping | python-jobspy (LinkedIn, Indeed, Google Jobs) |
| RSS parsing | feedparser (WeWorkRemotely) |
| PDF parsing | pdfplumber |
| CLI | Rich + questionary |
| Scheduler | APScheduler (embedded, no system cron) |
| Config — Python | Per-concern Pydantic models in `config/` and `config/sources/` |
| Config — Data | Per-source YAML files in `config/yaml/sources/` |
| Secrets | `.env` (gitignored); loaded via python-dotenv |

---

## 12. Build Sequence

| Phase | What ships | Risk |
|-------|-----------|------|
| **Phase 1** | Profile Agent + Discovery+Match Agent + Reporter. Fully read-only, no outbound. | Zero |
| **Phase 2** | Draft Agent + CLI approval queue + Send Executor (sandbox first). Switch LLM to cloud model. | Gated behind approval |
| **Phase 3** | Follow-up Agent + learning distillation loop. | Low — approval gate already in place |

**Phase 1 is the current target.** Nothing in Phase 1 touches the outside world on your behalf.
