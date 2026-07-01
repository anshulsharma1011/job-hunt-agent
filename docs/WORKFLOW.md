# Job Hunt Agent — System Workflow

**Phase:** 1 (read-only — no outbound actions)
**Model:** llama3.1:8b via Ollama (local, no API key required)
**Storage:** MongoDB (local)

---

## Overview

The agent runs as a CLI command (`job-hunt run`). Each run is called a **cycle**. A cycle fetches job listings from multiple sources, deduplicates them against everything it has ever seen, scores the fresh ones against your profile using an LLM, and writes a ranked report. Nothing leaves your machine.

```
User
 │
 ▼
job-hunt run
 │
 ▼
CLI (Click + Rich)
 │  checks DB for existing profile
 │  if none → parses resume PDF first
 │
 ▼
Orchestrator (LangGraph state machine)
 │
 ├─► load_profile_node
 │       read active profile from MongoDB
 │
 ├─► run_discovery_match_node
 │       fetch all sources → dedup → cap → score each job (LLM)
 │
 ├─► store_results_node
 │       upsert scored opportunities + update cycle record
 │
 └─► run_reporter_node
         write ranked .txt report to output/
```

---

## Step-by-Step Walkthrough

### 1. Session Start

```bash
source ./scale_up.sh    # starts MongoDB + Ollama, activates venv
job-hunt run
```

### 2. Profile Check

The CLI queries MongoDB for an **active profile** before starting the graph.

- **Profile exists** → skip to orchestrator
- **No profile** → run the Profile Agent: extract text from `materials/resume.pdf` → send to LLM → parse into structured `ProfileDoc` → save to MongoDB

`ProfileDoc` contains:
- `seniority` (junior / mid / senior / staff)
- `experience_years`
- `skills` (list of strings)
- `preferences.titles`, `preferences.locations`, `preferences.remote`

### 3. Orchestrator — LangGraph Graph

The orchestrator is a LangGraph state machine. It executes four nodes in sequence, passing a shared `CycleState` dict between them.

```
load_profile → run_discovery_match → store_results → run_reporter
```

Each node returns only the keys it modifies. The orchestrator owns all state transitions and logs — agents and repositories never advance lifecycle state or log transitions.

---

### 4. Discovery + Match Agent

This is the most complex step. It runs inside `run_discovery_match_node`.

#### 4a. Fetch All Sources

The agent iterates every registered source and calls `source.fetch(criteria)`:

| Source | Policy | Notes |
|--------|--------|-------|
| Greenhouse | `allowed` | API-based; fetches per-company job boards for ~140 configured companies |
| Adzuna | `allowed` | REST API; requires free API key |
| RemoteOK | `allowed` | Public JSON feed |
| WeWorkRemotely | `allowed` | Public RSS feed |
| LinkedIn | `allowed` | Scraped via jobspy |
| Indeed | `allowed` | Scraped via jobspy |
| Naukri | `human-assisted` | **Always skipped** — raises `SourceBlockedError` before fetch |

Before each fetch, `apply_source_policy()` is called. `blocked` and `human-assisted` sources raise `SourceBlockedError` and are skipped. Only `allowed` sources are fetched.

All fetched jobs are combined into a single list (`raw`).

#### 4b. Deduplication

`apply_dedup()` queries MongoDB for all external IDs already seen across every previous cycle. Any job whose `external_id` already exists in the DB is dropped.

```
fetched: 192 jobs
known:    10 (from previous cycle)
output:  182 fresh jobs
```

This is the key mechanism that prevents the same job from being scored twice, ever.

#### 4c. Cap

After dedup, the list is sliced to `max_per_cycle` (default: 10). This limits LLM cost per run. Only fresh jobs count toward the cap — so each cycle always processes 10 truly new jobs.

#### 4d. LLM Scoring

Each fresh job is sent to the LLM with:
- The job's company, title, location, and raw description
- The user's seniority, years of experience, skills, and role/location preferences

The LLM returns a structured JSON object:

```json
{
  "score": 83,
  "fit_rationale": ["Strong backend focus", "Remote-friendly"],
  "red_flags": ["Requires Java experience"],
  "recommended_track": "apply"
}
```

**Score range:** 0–100. Jobs scoring ≥ 70 are **shortlisted**; below 70 are **rejected**.

**Crash recovery:** Each job is written to MongoDB **immediately** after scoring via `upsert_one`. If the process crashes mid-cycle, the next run picks up from where it left off — already-scored jobs in the current cycle are skipped.

**Concurrency:** Controlled by `max_concurrent_scoring` (default: 1 for local Ollama — the model is single-threaded).

---

### 5. Store Results Node

After scoring, `store_results_node` upserts the complete list (shortlisted + rejected) via `upsert_many` — this is a no-op for jobs already written by `upsert_one` during scoring. It also updates the cycle record with counts and token spend.

---

### 6. Reporter Agent

`run_reporter_node` calls the Reporter Agent, which generates a plain-text report at:

```
output/cycle_<cycle_id>_report.txt
```

The report lists shortlisted jobs sorted by score descending, with fit rationale and recommended track per job.

---

### 7. CLI Output

The CLI prints a summary table:

```
 Cycle Complete
 Discovered   192
 Shortlisted   10
 Rejected       0
 Token spend  4841 tokens
 Report       output/cycle_a4a450a5_report.txt
```

---

## Data Flow Diagram

```
materials/resume.pdf
        │
        ▼ (first run only)
  Profile Agent
  (LLM: extract structured profile)
        │
        ▼
  MongoDB: profiles
        │
        ▼
  Orchestrator reads profile
        │
        ▼
  Sources (Greenhouse, Adzuna, RemoteOK, WeWorkRemotely, LinkedIn, Indeed)
        │  fetch(criteria)
        ▼
  RawOpportunity list  (192 jobs)
        │
        ▼  apply_dedup → drop known external_ids
  Fresh list  (182 jobs)
        │
        ▼  cap to max_per_cycle
  Batch  (10 jobs)
        │
        ▼  for each job: LLM score → upsert_one → MongoDB
  ScoredOpportunity list
        │
        ├─► score ≥ 70 → shortlisted
        └─► score < 70 → rejected
                │
                ▼
  MongoDB: opportunities
                │
                ▼
  Reporter Agent → output/cycle_<id>_report.txt
```

---

## MongoDB Collections

| Collection | Contents |
|------------|----------|
| `profiles` | Active user profile (parsed from resume) |
| `opportunities` | Every scored job ever seen — shortlisted and rejected |
| `cycles` | One record per `job-hunt run` with counts, token spend, report path |

---

## Dedup Correctness

The dedup check queries `opportunities` for all known `external_id` values **before** the cap is applied. This is intentional:

- **Wrong order (cap → dedup):** Greenhouse returns 200 jobs. Cap slices to 10. Dedup finds those 10 are already known. Score nothing. Repeat forever — the system never advances.
- **Correct order (dedup → cap):** Greenhouse returns 200 jobs. Dedup removes the 10 already known. 190 fresh remain. Cap slices to 10 new ones to score. Next cycle, those 10 are known; the next 10 fresh ones are scored. The system always makes progress.

---

## Configuration

| File | Key settings |
|------|-------------|
| `config/yaml/matching.yaml` | `score_threshold: 70`, `max_per_cycle: 10`, `max_concurrent_scoring: 1` |
| `config/yaml/llm.yaml` | `model: ollama/llama3.1:8b`, `timeout_seconds: 120`, `token_budget_per_cycle: 50000` |
| `config/yaml/sources/greenhouse.yaml` | `companies:` list — controls which company job boards are scraped |
| `config/yaml/log.yaml` | `log_level: DEBUG` — per-job scores, dedup counts, DB writes all visible |

---

## Hook Layer

Five cross-cutting hooks run at orchestrator level — never inside agents:

| Hook | When it runs | What it does |
|------|-------------|-------------|
| `apply_source_policy` | Before each source fetch | Blocks `blocked` and `human-assisted` sources |
| `apply_dedup` | After all sources fetched | Removes already-seen external IDs |
| `validate_output_schema` | After LLM response | Raises `SchemaValidationError` if response shape is wrong |
| `apply_budget_gate` | After scoring batch | Raises `BudgetExceededError` if token spend exceeds budget |
| `apply_rate_limit` | Before each source fetch | Enforces per-source request rate limits |

---

## Phase 1 Boundaries

Phase 1 is strictly read-only from the outside world's perspective:

- No emails sent
- No applications submitted
- No external API writes
- No headless browser automation
- Naukri is permanently `human-assisted` — never auto-fetched

The only output is MongoDB writes and `.txt` report files in `output/`.
