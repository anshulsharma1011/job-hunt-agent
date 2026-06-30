# Job Hunt Agent

An AI-powered, locally-run agent that discovers, scores, and ranks job opportunities against your profile — and in later phases, drafts applications and outreach for your approval before anything leaves the system.

---

## Quick Start

```bash
git clone https://github.com/vladput6969/job-hunt-agent.git
cd job-hunt-agent
source ./scale_up.sh
```

`scale_up.sh` installs and configures everything: Homebrew, Python 3.12, MongoDB, Ollama, the `llama3.1:8b` model, the Python virtualenv, and your `.env` file. Sourcing it also activates the venv in your current shell so you can run the agent immediately. Safe to re-run.

Once setup is done:

```bash
job-hunt run                                    # full cycle: profile check → fetch → score → report
job-hunt profile setup materials/resume.pdf     # parse resume and save profile
job-hunt profile show                           # view active profile
job-hunt report                                 # print latest cycle report
job-hunt status                                 # print last cycle summary
```

When you're done:

```bash
source ./scale_down.sh
```

See [RUNBOOK.md](docs/RUNBOOK.md) for the full command reference, config options, and troubleshooting.

---

## Session Scripts

Always use `source` so the scripts can activate/deactivate the venv in your shell.

| Script | What it does |
|--------|-------------|
| `source ./scale_up.sh` | Install prerequisites, start MongoDB + Ollama, create venv, install dependencies, activate venv |
| `source ./scale_down.sh` | Stop MongoDB + Ollama, kill llama-server, deactivate venv |

---

## Documentation

| Doc | Description |
|-----|-------------|
| [RUNBOOK.md](docs/RUNBOOK.md) | CLI commands, config reference, troubleshooting |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, design principles, agent roster |
| [HLD.md](docs/HLD.md) | High Level Design — components, tech stack, phased delivery |

---

## Phases

- **Phase 1 (current):** Profile parsing → job discovery → scoring → ranked report. No outbound.
- **Phase 2:** Draft generation → CLI approval queue → send executor.
- **Phase 3:** Learning loop → follow-up agent → outreach effectiveness tracking.
