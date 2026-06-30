# T11-adhoc — Structured Logging

**Status:** `pending`
**Depends on:** T2 (config layer)

## Goal

Production-grade logging where DEBUG mode gives a full cycle trace without
querying MongoDB. Every log line carries `cycle_id` for correlation.

---

## Log Levels

| Level | What is logged |
|---|---|
| `DEBUG` | Node entry/exit + state diff, agent input/output, LLM prompt + response + tokens, DB read/write operations, hook evaluations, source fetch results |
| `INFO` | Cycle start/end, node transitions (name + duration), counts (discovered/shortlisted/rejected), token spend summary, report path |
| `WARNING` | Retries, fallbacks, near-budget threshold |
| `ERROR` | Unhandled exceptions, LLM failures after retry, schema validation failures |

---

## Files to Create / Modify

```
config/log_config.py          ← LogConfig Pydantic model (log_level, log_to_file, log_dir)
config/yaml/app.yaml          ← add log_level: INFO, log_to_file: true, log_dir: output/logs
config/app_config.py          ← add log: LogConfig field
logging_setup.py              ← setup_logging(config) — called once at startup in main.py
```

Logging calls added to:
```
orchestrator/nodes.py         ← node entry, exit, state diff (DEBUG), transition (INFO)
agents/profile_agent.py       ← PDF extraction result (DEBUG), LLM call (DEBUG)
llm/client.py                 ← request prompt (DEBUG), response + tokens (DEBUG), timeout (ERROR)
store/repositories/*.py       ← each DB operation (DEBUG)
orchestrator/hooks.py         ← each hook result (DEBUG), budget warning (WARNING)
```

---

## `config/log_config.py`

```python
class LogConfig(BaseModel):
    log_level: str = "INFO"        # DEBUG | INFO | WARNING | ERROR
    log_to_file: bool = True
    log_dir: str = "output/logs"
```

---

## `logging_setup.py`

```python
def setup_logging(config: LogConfig) -> None:
    """
    Configures root logger. Call once at process startup.

    Handlers:
      - StreamHandler (stdout) — always on
      - RotatingFileHandler (output/logs/app.log) — when log_to_file=True
        max 10MB per file, keep 5 backups

    Format:
      - DEBUG/dev: human-readable  timestamp | LEVEL | module | cycle=... | message
      - Production: JSON — {"ts": ..., "level": ..., "module": ..., "cycle_id": ..., "msg": ...}
    """
```

---

## Correlation — `cycle_id` in Every Line

Use a `logging.LoggerAdapter` that injects `cycle_id` into every record:

```python
# logging_setup.py
class CycleAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[cycle={self.extra['cycle_id']}] {msg}", kwargs

def get_logger(name: str, cycle_id: str = "") -> logging.LoggerAdapter:
    logger = logging.getLogger(name)
    return CycleAdapter(logger, {"cycle_id": cycle_id})
```

Usage in nodes:
```python
log = get_logger(__name__, state["cycle_id"])
log.info("load_profile: started")
log.debug("load_profile: profile found — profile_id=%s", profile.profile_id)
log.info("load_profile: completed in %.3fs", elapsed)
```

---

## What DEBUG Mode Shows (no DB needed)

```
2026-07-01 10:00:00 | DEBUG | orchestrator.nodes | [cycle=abc123] load_profile: started
2026-07-01 10:00:00 | DEBUG | store.repositories.profile_repo | [cycle=abc123] get_active: query={is_active: true} → found profile_id=xyz
2026-07-01 10:00:00 | INFO  | orchestrator.nodes | [cycle=abc123] load_profile: completed in 0.012s → route=profile_exists
2026-07-01 10:00:01 | DEBUG | agents.profile_agent | [cycle=abc123] _extract_text: extracted 1842 chars from materials/resume.pdf
2026-07-01 10:00:01 | DEBUG | llm.client | [cycle=abc123] complete_json: model=llama3.1:8b schema=LLMProfileDraft prompt_chars=2100
2026-07-01 10:00:08 | DEBUG | llm.client | [cycle=abc123] complete_json: response_tokens=312 total_tokens=890
2026-07-01 10:00:08 | INFO  | orchestrator.nodes | [cycle=abc123] run_profile_agent: completed in 7.4s profile_id=xyz
...
2026-07-01 10:01:20 | INFO  | orchestrator.nodes | [cycle=abc123] cycle complete — discovered=42 shortlisted=8 rejected=34 tokens=4200 report=output/report_abc123.md
```

---

## Output

```
output/logs/
  app.log          ← current log file
  app.log.1        ← previous (rotated)
  app.log.2
  ...
```

`output/logs/` is gitignored (already covered by `output/` gitignore rule).

---

## Steps

1. `config/log_config.py` — LogConfig model
2. Update `config/yaml/app.yaml` and `config/app_config.py`
3. `logging_setup.py` — setup_logging + CycleAdapter + get_logger
4. Add logging calls to `orchestrator/nodes.py`
5. Add logging calls to `agents/profile_agent.py`
6. Add logging calls to `llm/client.py`
7. Add logging calls to `store/repositories/*.py`
8. Add logging calls to `orchestrator/hooks.py`
9. Call `setup_logging(config.log)` in `main.py`
10. Run `mypy` on all changed files
11. Run full test suite — no test changes required (logging is a side effect, not tested directly)
12. Manual smoke test: run the graph, verify DEBUG output matches the expected format above
