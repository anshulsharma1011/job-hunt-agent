# Job Hunt Agent — Claude Instructions

## Project Context

A locally-run, India-first AI agent that discovers, scores, and ranks job opportunities. Phase 1 is fully read-only — no outbound actions. Everything that could touch the outside world on the user's behalf is gated behind a human approval step (Phase 2+).

---

## Architecture Rules

**Agent boundaries — the most important rule.**
- Agents are pure functions: `(state slice) → updated state`. No side effects inside agents.
- Agents never call each other directly. All work is returned to the orchestrator.
- Agents never access MongoDB directly. All reads/writes go through the repository layer (`store/repositories/`).
- Agents never call the LLM directly. All LLM calls go through `llm/client.py` (LiteLLM wrapper).
- Only the orchestrator advances lifecycle state. No agent sets `lifecycle_state` on an opportunity.

**Orchestrator owns everything cross-cutting.**
- Hooks (dedup, rate limiter, schema validator, budget gate, source policy) live in `orchestrator/hooks.py` — never inside agents or sources.
- State transitions are logged in `orchestrator/nodes.py`. Never log transitions inside agents.
- LangGraph node functions live in `orchestrator/nodes.py`. Graph wiring lives in `orchestrator/graph.py`. Keep them separate.

**Send executor rule (Phase 2+).**
- Only `executor/send_executor.py` holds outbound credentials. No other file may import or reference them.
- In Phase 1 the send executor does not exist. Do not scaffold it prematurely.

---

## Code Structure

```
agents/          ← pure functions only, no IO, no DB, no direct LLM
orchestrator/    ← graph.py (wiring), nodes.py (node fns), hooks.py, router.py, state.py
sources/         ← one file per source, all extend base.JobSource
store/
  models.py      ← Pydantic schemas — single source of truth for all data shapes
  db.py          ← MongoDB connection only
  repositories/  ← all DB reads/writes live here, nowhere else
llm/
  client.py      ← LiteLLM wrapper — the only file that calls an LLM
cli/             ← Rich + questionary UI
scheduler/       ← APScheduler trigger only
output/          ← report files written here (gitignored)
materials/       ← user's resume PDF (gitignored)
```

---

## Python Conventions

- Python 3.12. Type hints on every function signature — no exceptions.
- Pydantic models for every data contract. Never pass raw `dict` between layers.
- No bare `except:` clauses. Always catch a specific exception type.
- Use `pathlib.Path` for all file paths — never string concatenation.
- Environment variables via `python-dotenv` loaded once in `config.py`. Never call `os.environ` directly in agents or repositories.
- All config values read from `config.yaml`. No hardcoded thresholds, model names, or source URLs in agent or orchestrator code.

---

## LangGraph Rules

- `CycleState` is defined in `orchestrator/state.py` and imported everywhere. Never redefine state shape inline.
- Node functions in `orchestrator/nodes.py` return only the keys they modify — never return the full state object.
- Conditional edge functions in `orchestrator/router.py` — never inline lambdas in `add_conditional_edges()`.
- The graph is compiled once in `orchestrator/graph.py` and imported by `main.py` and `scheduler/runner.py`. Never recompile the graph per-cycle.

---

## MongoDB / Repository Rules

- All collections are defined as constants in `store/db.py`. Never use a raw string collection name outside that file.
- Repository methods are the only place that call `insert_one`, `find`, `update_one`, etc.
- Every opportunity document must include a `history` array. Append a `{state, at}` entry on every lifecycle transition — never overwrite the array.
- Dedup check always happens in the orchestrator hook (`orchestrator/hooks.py`), not inside the Discovery+Match Agent or the repository.

---

## Source Policy Rules

- Every source class must declare a `policy` attribute: `"allowed"` | `"human-assisted"` | `"blocked"`.
- `source_policy.py` reads the policy table from `config.yaml` and is the single gate before any fetch. Never bypass it.
- No headless browser automation anywhere in the codebase (no Playwright, Puppeteer, Selenium imports).
- Naukri is `human-assisted` permanently — never change it to `allowed`.

---

## Phase Discipline

- **Phase 1 scope:** Profile Agent + Discovery+Match Agent + Reporter Agent + Orchestrator + Store + CLI trigger. Nothing else.
- Do not scaffold Draft Agent, Send Executor, Follow-up Agent, or approval queue UI during Phase 1, even as stubs.
- If a Phase 2 concern comes up during Phase 1 work, add a `# TODO Phase 2:` comment and move on — do not implement it.
- The `output/` directory is the only thing Phase 1 writes outside MongoDB. Nothing calls an external API or sends any network request on the user's behalf.

---

## Testing Rules

- Every agent must have a unit test that feeds a valid input message and asserts the output schema — no network calls, no DB calls in agent unit tests (mock the LLM client and repositories).
- Every hook in `orchestrator/hooks.py` must have a test with an adversarial input (e.g., dedup hook receives a duplicate opportunity ID; schema validator receives a malformed payload).
- Repository tests use a real local MongoDB connection against a `test_job_hunt` database — never mock the DB layer.
- Test files mirror the source structure: `tests/agents/`, `tests/orchestrator/`, `tests/sources/`, `tests/store/`.

---

## Commit Workflow

Before every commit, in this order:
1. Run `python -m pytest tests/` — all tests must pass.
2. Run `python -m mypy .` — no type errors on changed files.
3. Never commit without explicit user confirmation ("go ahead" or "commit it").
4. Never mention AI, Claude, or any AI tool in commit messages.
5. Never add `Co-Authored-By` lines to commit messages.
6. Always write a meaningful commit body — what changed and why, not just a title.

---

## Documentation

- Local docs are in `docs/`. Always update local docs first.
- `docs/ARCHITECTURE.md` — update when agent roster, orchestrator design, or tech stack decisions change.
- `docs/HLD.md` — update when phase scope, component responsibilities, or flow changes.
- Do not create new doc files without being asked.
