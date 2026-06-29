# T15 — Scheduler

**Status:** `pending`
**Depends on:** T10

## Goal
APScheduler cron trigger that fires the LangGraph graph on the configured schedule. Only activated when `scheduler.enabled: true` in config.

## Files to Create

```
scheduler/runner.py
```

## `scheduler/runner.py`

```python
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

def run_cycle(deps: Deps) -> None:
    """Single cycle execution — same logic as CLI `run` command."""
    graph = build_graph(deps)
    state = make_initial_state(cycle_id=f"cycle_{uuid4().hex[:8]}")
    result = graph.invoke(state)
    # log summary to stdout

def start_scheduler(config: AppConfig, deps: Deps) -> None:
    """Starts blocking scheduler. Only called if config.scheduler.enabled == True."""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_cycle,
        trigger=CronTrigger.from_crontab(config.scheduler.cron),
        kwargs={"deps": deps},
    )
    scheduler.start()
```

**`main.py` wiring:**
```python
if __name__ == "__main__":
    config = load_config()
    if config.scheduler.enabled:
        deps = build_deps(config)
        start_scheduler(config, deps)
    else:
        cli()
```

## Steps

1. Write `scheduler/runner.py` with `run_cycle()` and `start_scheduler()`
2. Update `main.py` to branch on `scheduler.enabled`
3. Manual test: set `scheduler.enabled: true`, cron to `"* * * * *"` (every minute), verify cycle fires
4. Reset `scheduler.enabled: false` after test
5. Commit
