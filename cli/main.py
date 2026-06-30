from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import click
from rich.console import Console
from rich.table import Table

from agents.discovery_match_agent import DiscoveryMatchAgent
from agents.profile_agent import ProfileAgent
from agents.reporter_agent import ReporterAgent
from config.app_config import AppConfig
from config.loader import load_config
from llm.client import LLMClient
from logging_setup import setup_logging
from orchestrator.deps import Deps
from orchestrator.graph import build_graph, make_initial_state
from sources.registry import build_source_registry
from store.cycle_record import CycleRecord
from store.db import get_client, get_db
from store.repositories.cycle_repo import CycleRepository
from store.repositories.opportunity_repo import OpportunityRepository
from store.repositories.profile_repo import ProfileRepository

console = Console()


def _build_deps(config: AppConfig) -> Deps:
    mongo_client = get_client(config.mongodb)
    db = get_db(config.mongodb)
    llm = LLMClient(config.llm)
    sources = build_source_registry(config)
    return Deps(
        config=config,
        mongo_client=mongo_client,
        db=db,
        profile_repo=ProfileRepository(db),
        opportunity_repo=OpportunityRepository(db),
        cycle_repo=CycleRepository(db),
        source_registry=sources,
        profile_agent=ProfileAgent(llm),
        discovery_match_agent=DiscoveryMatchAgent(llm, sources, config),
        reporter_agent=ReporterAgent(),
    )


@click.group()
def cli() -> None:
    """Job Hunt Agent — discover, score, and rank job opportunities."""


@cli.command()
def run() -> None:
    """Trigger a full cycle: profile → discovery → scoring → report."""
    config = load_config()
    setup_logging(config.log)
    deps = _build_deps(config)

    if deps.profile_repo.get_active() is None:
        resume_path = Path(config.app.resume_path)
        if not resume_path.exists():
            console.print(f"[red]No profile found and resume not at:[/red] {resume_path}")
            console.print("Run: job-hunt profile setup <pdf_path>")
            return
        with console.status(f"No profile found — parsing resume {resume_path}…", spinner="dots"):
            profile_result = deps.profile_agent.run(resume_path)
        deps.profile_repo.save(profile_result["profile_doc"])
        console.print(f"[green]✓[/green] Profile parsed — seniority={profile_result['profile_doc'].seniority}")
    else:
        console.print("[green]✓[/green] Profile loaded from DB")

    cycle_id = str(uuid4())
    deps.cycle_repo.create(CycleRecord(cycle_id=cycle_id, started_at=datetime.now(timezone.utc)))
    console.print(f"[bold]Starting cycle[/bold] {cycle_id}")

    graph = build_graph(deps)
    with console.status("Running discovery + scoring…", spinner="dots"):
        final_state = graph.invoke(
            make_initial_state(cycle_id),
            config={"configurable": {"thread_id": cycle_id}},
        )

    table = Table(title="Cycle Complete", show_header=False, box=None)
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Discovered", str(len(final_state["raw_opportunities"])))
    table.add_row("Shortlisted", f"[green]{len(final_state['shortlisted'])}[/green]")
    table.add_row("Rejected", str(len(final_state["rejected"])))
    table.add_row("Token spend", f"{float(final_state['token_spend']):.0f} tokens")
    table.add_row("Report", str(final_state.get("report_path", "—")))
    console.print(table)


@cli.group()
def profile() -> None:
    """Manage the candidate profile."""


@profile.command("setup")
@click.argument("pdf_path", type=click.Path(exists=True))
def profile_setup(pdf_path: str) -> None:
    """Parse a resume PDF and save it as the active profile."""
    config = load_config()
    setup_logging(config.log)
    deps = _build_deps(config)

    with console.status("Parsing resume…", spinner="dots"):
        result = deps.profile_agent.run(Path(pdf_path))

    profile_doc = result["profile_doc"]
    deps.profile_repo.save(profile_doc)

    console.print(f"[green]✓[/green] Profile saved  profile_id={profile_doc.profile_id}")
    console.print(f"  Seniority       : {profile_doc.seniority}")
    console.print(f"  Experience      : {profile_doc.experience_years} years")
    console.print(f"  Skills          : {', '.join(profile_doc.skills[:8])}")
    console.print(f"  Preferred roles : {', '.join(profile_doc.preferences.titles[:3])}")


@profile.command("show")
def profile_show() -> None:
    """Print the active profile summary."""
    config = load_config()
    setup_logging(config.log)
    deps = _build_deps(config)

    doc = deps.profile_repo.get_active()
    if doc is None:
        console.print("[yellow]No active profile found.[/yellow] Run: python main.py profile setup <pdf_path>")
        return

    table = Table(title="Active Profile", show_header=False, box=None)
    table.add_column(style="dim", min_width=18)
    table.add_column()
    table.add_row("Profile ID", doc.profile_id)
    table.add_row("Seniority", doc.seniority)
    table.add_row("Experience", f"{doc.experience_years} years")
    table.add_row("Skills", ", ".join(doc.skills))
    table.add_row("Preferred roles", ", ".join(doc.preferences.titles))
    table.add_row("Locations", ", ".join(doc.preferences.locations))
    table.add_row("Remote", "yes" if doc.preferences.remote else "no")
    if doc.preferences.comp_min_lpa:
        table.add_row("Min comp (LPA)", str(doc.preferences.comp_min_lpa))
    console.print(table)


@cli.command()
def report() -> None:
    """Print the latest cycle report to the terminal."""
    config = load_config()
    setup_logging(config.log)
    deps = _build_deps(config)

    cycle = deps.cycle_repo.get_latest()
    if cycle is None:
        console.print("[yellow]No cycles found.[/yellow] Run: python main.py run")
        return
    if not cycle.report_path:
        console.print("[yellow]Latest cycle has no report yet.[/yellow]")
        return

    path = Path(cycle.report_path)
    if not path.exists():
        console.print(f"[red]Report file not found:[/red] {path}")
        return

    console.print(path.read_text(encoding="utf-8"))


@cli.command()
def status() -> None:
    """Print the last cycle summary."""
    config = load_config()
    setup_logging(config.log)
    deps = _build_deps(config)

    cycle = deps.cycle_repo.get_latest()
    if cycle is None:
        console.print("[yellow]No cycles found.[/yellow] Run: python main.py run")
        return

    completed = cycle.completed_at.strftime("%Y-%m-%d %H:%M UTC") if cycle.completed_at else "in progress"

    table = Table(title="Last Cycle", show_header=False, box=None)
    table.add_column(style="dim", min_width=16)
    table.add_column()
    table.add_row("Cycle ID", cycle.cycle_id)
    table.add_row("Started", cycle.started_at.strftime("%Y-%m-%d %H:%M UTC"))
    table.add_row("Completed", completed)
    table.add_row("Sources", ", ".join(cycle.sources_queried) or "—")
    table.add_row("Discovered", str(cycle.discovered_count))
    table.add_row("Shortlisted", f"[green]{cycle.shortlisted_count}[/green]")
    table.add_row("Rejected", str(cycle.rejected_count))
    table.add_row("Token spend", f"{cycle.token_spend:.0f} tokens")
    table.add_row("Report", cycle.report_path or "—")
    if cycle.errors:
        table.add_row("Errors", f"[red]{len(cycle.errors)}[/red]")
    console.print(table)
