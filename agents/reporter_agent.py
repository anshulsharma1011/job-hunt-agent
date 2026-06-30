from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.app_config import AppConfig
from orchestrator.state import CycleState
from store.scored_opportunity import ScoredOpportunity

_log = logging.getLogger(__name__)

_DIVIDER = "═" * 59
_SECTION = "─" * 59
_TOP_N = 10


class ReporterAgent:
    def __init__(self) -> None:
        pass

    def run(self, state: CycleState, config: AppConfig) -> dict[str, object]:
        output_dir = Path(config.output.report_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        shortlisted = [ScoredOpportunity.model_validate(d) for d in state["shortlisted"]]
        rejected = [ScoredOpportunity.model_validate(d) for d in state["rejected"]]

        content = self._format_report(state, config, shortlisted, rejected)
        report_path = self._write(content, state["cycle_id"], output_dir)
        _log.info(
            "run: report written shortlisted=%d rejected=%d path=%s",
            len(shortlisted),
            len(rejected),
            report_path,
        )
        return {"report_path": str(report_path)}

    def _format_report(
        self,
        state: CycleState,
        config: AppConfig,
        shortlisted: list[ScoredOpportunity],
        rejected: list[ScoredOpportunity],
    ) -> str:
        run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        threshold = config.matching.score_threshold
        sources = ", ".join(state["sources_queried"]) or "—"
        token_spend = float(state["token_spend"])

        lines: list[str] = [
            "JOB HUNT AGENT — CYCLE REPORT",
            _DIVIDER,
            f"Cycle ID    : {state['cycle_id']}",
            f"Run at      : {run_at}",
            f"Model       : {config.llm.model}",
            f"Token spend : {token_spend:.2f} (local Ollama)" if token_spend == 0 else f"Token spend : {token_spend:.0f} tokens",
            "",
            "SUMMARY",
            f"  Discovered  : {len(state['raw_opportunities'])}",
            f"  Shortlisted : {len(shortlisted)}  (score ≥ {threshold})",
            f"  Rejected    : {len(rejected)}",
            f"  Sources     : {sources}",
        ]

        sorted_shortlisted = sorted(shortlisted, key=lambda o: o.score, reverse=True)

        if sorted_shortlisted:
            lines += ["", "TOP MATCHES", _SECTION]
            for rank, opp in enumerate(sorted_shortlisted[:_TOP_N], start=1):
                raw = opp.raw
                fit = "  ".join(f"✓ {r}" for r in opp.fit_rationale)
                flags = "  ".join(f"✗ {f}" for f in opp.red_flags) if opp.red_flags else "  (none)"
                lines += [
                    f"#{rank:<3} {raw.role_title} — {raw.company:<30} {opp.score}",
                    f"    Location : {raw.location}  |  Track : {opp.recommended_track.value}",
                    f"    Fit      : {fit}" if opp.fit_rationale else "    Fit      : —",
                    f"    Flags    : {flags}",
                    f"    URL      : {raw.source_url}",
                    "",
                ]
            if len(sorted_shortlisted) > _TOP_N:
                lines.append(f"  … and {len(sorted_shortlisted) - _TOP_N} more in MongoDB opportunities collection.")
                lines.append("")
        else:
            lines += ["", "TOP MATCHES", _SECTION, "  No shortlisted roles this cycle.", ""]

        lines += [
            f"BELOW THRESHOLD ({len(rejected)} roles archived)",
            "  See MongoDB opportunities collection for full details.",
            _DIVIDER,
        ]

        return "\n".join(lines)

    def _write(self, content: str, cycle_id: str, output_dir: Path) -> Path:
        path = output_dir / f"cycle_{cycle_id}_report.txt"
        path.write_text(content, encoding="utf-8")
        return path
