# Job Hunt Agent — WBS (Phase 1)

## Task Status

| ID | Task | Status | Depends On | Plan |
|----|------|--------|------------|------|
| T1 | Project Scaffold | `done` | — | [T1-scaffold.md](plans/T1-scaffold.md) | `requirements.txt`, `.env.example`, `.gitignore`, `main.py`, all `__init__.py`, `output/.gitkeep`, `materials/.gitkeep` |
| T2 | Config Layer | `done` | T1 | [T2-config.md](plans/T2-config.md) |
| T3 | Store — Models | `done` | T2 | [T3-models.md](plans/T3-models.md) |
| T4 | Store — DB + Repositories | `done` | T3 | [T4-repositories.md](plans/T4-repositories.md) |
| T5 | LLM Client | `done` | T2 | [T5-llm-client.md](plans/T5-llm-client.md) |
| T6 | Prompt Templates | `done` | T1 | [T6-prompts.md](plans/T6-prompts.md) |
| T7 | Source Layer | `done` | T2, T3 | [T7-sources.md](plans/T7-sources.md) |
| T8 | Orchestrator — State + Errors + Router | `done` | T3 | [T8-orch-state.md](plans/T8-orch-state.md) |
| T9 | Orchestrator — Hooks | `done` | T4, T7, T8 | [T9-orch-hooks.md](plans/T9-orch-hooks.md) |
| T10 | Orchestrator — Nodes + Graph | `done` | T5, T6, T8, T9 | [T10-orch-graph.md](plans/T10-orch-graph.md) |
| T11 | Profile Agent | `done` | T5, T6 | [T11-profile-agent.md](plans/T11-profile-agent.md) |
| T11-adhoc | Structured Logging | `done` | T2 | [T11-adhoc-logging.md](plans/T11-adhoc-logging.md) |
| T12 | Discovery + Match Agent | `done` | T5, T6, T7 | [T12-discovery-agent.md](plans/T12-discovery-agent.md) |
| T13 | Reporter Agent | `pending` | T3 | [T13-reporter-agent.md](plans/T13-reporter-agent.md) |
| T14 | CLI | `pending` | T10, T11, T12, T13 | [T14-cli.md](plans/T14-cli.md) |
| T15 | Scheduler | `pending` | T10 | [T15-scheduler.md](plans/T15-scheduler.md) |
| T16 | Unit Tests — Agents + Hooks | `pending` | T11, T12, T13, T9 | [T16-unit-tests.md](plans/T16-unit-tests.md) |
| T17 | Integration Tests — Repositories | `pending` | T4 | [T17-integration-tests.md](plans/T17-integration-tests.md) |
| T18 | End-to-End Smoke Test | `pending` | T14, T16, T17 | [T18-e2e.md](plans/T18-e2e.md) |
| T19 | Greenhouse Slug Store (Enhancement) | `pending` | T4, T7 | — |
| T20 | Config Layer Restructure (Enhancement) | `done` | T2 | — |
| T21 | Glassdoor Source (Enhancement) | `pending` | T7 | — |

---

## Dependency Graph

```
T1 (scaffold)
 └── T2 (config)
      ├── T3 (models)
      │    ├── T4 (db + repos) ──────────────────────────────┐
      │    ├── T7 (sources)                                   │
      │    └── T8 (orch: state + errors + router)            │
      │         └── T9 (orch: hooks) ── needs T4, T7 ────────┤
      │              └── T10 (orch: nodes + graph) ──────────┤
      │                   needs T5, T6, T8, T9               │
      ├── T5 (llm client)                                     │
      └── T6 (prompts) [needs T1]                            │
                                                              │
T10 + T11 + T12 + T13 ──► T14 (CLI)                         │
T10 ──────────────────────► T15 (scheduler)                  │
T9 + T11–T13 ─────────────► T16 (unit tests)                │
T4 ────────────────────────► T17 (integration tests) ◄───────┘
T14 + T16 + T17 ──────────► T18 (e2e smoke test)
T4 + T7 ───────────────────► T19 (greenhouse slug store) [enhancement — post Phase 1]
```

---

## Enhancements (Post Phase 1)

| ID | Enhancement | Notes |
|----|-------------|-------|
| T19 | Greenhouse Slug Store | Move Greenhouse company slugs from `config/sources.yaml` into a MongoDB `greenhouse_slugs` collection. `GreenhouseSource.fetch()` reads slugs from DB so the list can grow to 1000+ without bloating config. Seed script loads from `scripts/greenhouse_candidates.py`. |
| T20 | Config Layer Restructure | Separated YAML data from Python models. Data lives in `config/yaml/` (one file per concern, per-source files under `config/yaml/sources/`). Python models live in `config/sources/` (one class per source: `GreenhouseConfig`, `AdzunaConfig`, `IndeedConfig`, etc., all extending `SourcePolicyBase`). Replaced the single catch-all `SourcePolicyConfig` class with a typed `SourcesConfig` aggregate; sources are accessed as typed attributes (`config.sources.greenhouse`, `config.sources.indeed`) with no Optional guards. |
| T21 | Glassdoor Source (Enhancement) | Add `GlassdoorSource(JobSpyBase)` with `site_name="glassdoor"`. Glassdoor returns salary range data (`min_amount`, `max_amount`, `currency`) which the scoring agent can use to rank opportunities. Implement as a 2-line subclass of `JobSpyBase` following the same pattern as `LinkedInSource`. |
