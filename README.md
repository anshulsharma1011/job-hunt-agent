# Job Hunt Agent

An AI-powered, locally-run agent that discovers, scores, and ranks job opportunities against your profile — and in later phases, drafts applications and outreach for your approval before anything leaves the system.

---

## Documentation

| Doc | Description |
|-----|-------------|
| [PREREQUISITES.md](docs/PREREQUISITES.md) | What to install before anything else — written for a fresh machine |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Original system architecture and design principles |
| [HLD.md](docs/HLD.md) | High Level Design — components, tech stack, phased delivery |

LLD and setup guides will be added as implementation progresses.

---

## Phases

- **Phase 1 (current):** Profile parsing → job discovery → scoring → ranked report. No outbound.
- **Phase 2:** Draft generation → CLI approval queue → send executor.
- **Phase 3:** Learning loop → follow-up agent → outreach effectiveness tracking.
