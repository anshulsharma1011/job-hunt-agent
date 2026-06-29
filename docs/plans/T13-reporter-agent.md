# T13 — Reporter Agent

**Status:** `pending`
**Depends on:** T3

## Goal
Read cycle data and write a `.txt` report to `output/`. Read-only — never triggers any action, no LLM call, no DB write.

## Files to Create

```
agents/reporter_agent.py
tests/agents/test_reporter_agent.py
```

## `agents/reporter_agent.py`

```python
class ReporterAgent:
    def __init__(self, output_dir: Path):
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        cycle_id: str,
        shortlisted: list[ScoredOpportunity],
        rejected: list[ScoredOpportunity],
        meta: CycleRecord,
    ) -> Path:
        content = self._format_report(cycle_id, shortlisted, rejected, meta)
        return self._write(content, cycle_id)

    def _format_report(self, ...) -> str:
        """Builds the full report string. See report format below."""

    def _write(self, content: str, cycle_id: str) -> Path:
        path = self._output_dir / f"cycle_{cycle_id}_report.txt"
        path.write_text(content, encoding="utf-8")
        return path
```

## Report Format

```
JOB HUNT AGENT — CYCLE REPORT
═══════════════════════════════════════════════════════════
Cycle ID    : cycle_abc123
Run at      : 2026-06-29 18:00 IST
Model       : ollama/llama3.1:8b
Token spend : 0.00 USD (local Ollama)

SUMMARY
  Discovered  : 47
  Shortlisted : 12  (score ≥ 70)
  Rejected    : 35
  Sources     : greenhouse, indeed, linkedin

TOP MATCHES
───────────────────────────────────────────────────────────
#1  Senior Backend Engineer — Razorpay                   87
    Location : Bangalore / Remote  |  Track : apply
    Fit      : ✓ Python + distributed systems match
               ✓ Fintech domain aligns with experience
               ✓ Remote-friendly matches preference
    Flags    : ✗ Requires 10+ years (you have 8)
    URL      : https://boards.greenhouse.io/...

[... top 10 shortlisted roles ...]

BELOW THRESHOLD (35 roles archived)
  See MongoDB opportunities collection for full details.
═══════════════════════════════════════════════════════════
```

## Tests

```
tests/agents/test_reporter_agent.py
  - test_run_creates_report_file
  - test_report_contains_shortlisted_roles
  - test_report_contains_summary_counts
  - test_report_file_named_with_cycle_id
  - test_run_makes_no_llm_or_db_calls       # assert no side effects
```

## Steps

1. Write `ReporterAgent.__init__` — ensure output dir exists
2. Write `_format_report()` — build report string per format above
3. Write `_write()` — write to file, return path
4. Write `run()` — call both, return path
5. Write tests — use `tmp_path` pytest fixture for output dir
6. Run `pytest tests/agents/test_reporter_agent.py` — must pass
7. Run `mypy agents/reporter_agent.py` — must pass
8. Commit
