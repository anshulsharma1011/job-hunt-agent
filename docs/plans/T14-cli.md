# T14 — CLI

**Status:** `pending`
**Depends on:** T10, T11, T12, T13

## Goal
Click + Rich CLI with commands to trigger a cycle, manage the profile, and view reports.

## Files to Create

```
cli/main.py
main.py
```

## Commands

```
python main.py run                        # trigger a full cycle
python main.py profile setup <pdf_path>  # run Profile Agent on a PDF
python main.py profile show              # print active profile summary
python main.py report                    # print latest report to terminal
python main.py status                    # print last cycle summary table
```

## `cli/main.py`

```python
import click
from rich.console import Console
from rich.table import Table

console = Console()

@click.group()
def cli(): ...

@cli.command()
def run():
    """Trigger a full discovery + scoring cycle."""
    config = load_config()
    deps = build_deps(config)
    graph = build_graph(deps)
    state = make_initial_state(cycle_id=f"cycle_{uuid4().hex[:8]}")
    result = graph.invoke(state)
    # print Rich summary: shortlisted count, rejected count, report path

@cli.group()
def profile(): ...

@profile.command("setup")
@click.argument("pdf_path", type=click.Path(exists=True))
def profile_setup(pdf_path: str):
    """Parse PDF resume and save as active profile."""
    # calls ProfileAgent.run() + ProfileRepository.save()

@profile.command("show")
def profile_show():
    """Print active profile as a Rich table."""
    # reads ProfileRepository.get_active(), prints via Rich

@cli.command()
def report():
    """Print the latest cycle report to terminal."""
    # reads latest CycleRecord.report_path, prints file contents

@cli.command()
def status():
    """Print last cycle summary."""
    # reads CycleRepository.get_latest(), prints Rich table
```

## `build_deps()` helper

```python
def build_deps(config: AppConfig) -> Deps:
    mongo_client = get_client(config.mongodb)
    db = get_db(config.mongodb)
    return Deps(
        config=config,
        mongo_client=mongo_client,
        llm=LLMClient(config.llm),
        sources=build_source_registry(config),
        profile_repo=ProfileRepository(db),
        opportunity_repo=OpportunityRepository(db),
        cycle_repo=CycleRepository(db),
        profile_agent=ProfileAgent(LLMClient(config.llm)),
        discovery_agent=DiscoveryMatchAgent(LLMClient(config.llm), build_source_registry(config), config),
        reporter_agent=ReporterAgent(Path(config.output.report_dir)),
    )
```

## Steps

1. Write `cli/main.py` with all 5 commands
2. Write `build_deps()` helper
3. Write `main.py` entrypoint
4. Manual test: run `python main.py --help` — all commands listed
5. Manual test: run `python main.py profile show` with no profile — should print "No active profile found"
6. Commit
