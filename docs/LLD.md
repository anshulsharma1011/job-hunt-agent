# Job Hunt Agent — Low Level Design

**Status:** Phase 1 scope only
**Last updated:** 2026-06-29

---

## 1. Configuration Files (`config/`)

Config is split by concern. No hardcoded values in agent or orchestrator code. All files loaded and merged at startup by `config/loader.py` into a single `AppConfig` Pydantic model.

```
config/
├── app.yaml          # app identity and environment
├── llm.yaml          # model, endpoint, budget
├── matching.yaml     # scoring thresholds and concurrency
├── sources.yaml      # per-source policy, limits, and settings
├── mongodb.yaml      # connection and database names
├── scheduler.yaml    # cron schedule and toggle
└── output.yaml       # report directory and format
```

---

### `config/app.yaml`

```yaml
name: job-hunt-agent
env: development              # development | production
```

---

### `config/llm.yaml`

```yaml
model: ollama/llama3.1:8b
base_url: http://localhost:11434
timeout_seconds: 120
token_budget_per_cycle: 50000   # hard stop — not a suggestion
```

---

### `config/matching.yaml`

```yaml
score_threshold: 70             # opportunities below this are rejected
max_per_cycle: 100              # cap raw opportunities fetched per cycle
max_concurrent_scoring: 5       # parallel LLM scoring calls
```

---

### `config/sources.yaml`

```yaml
greenhouse:
  policy: allowed
  enabled: true
  companies: []                 # empty = curated list; slugs = filter to these only
  max_per_run: 50

indeed:
  policy: allowed
  enabled: true
  location: "India"
  max_per_run: 50

linkedin:
  policy: allowed
  enabled: true
  max_requests_per_cycle: 5

naukri:
  policy: human-assisted
  enabled: true
```

---

### `config/mongodb.yaml`

```yaml
uri: mongodb://localhost:27017
database: job_hunt_db
test_database: test_job_hunt_db
```

---

### `config/scheduler.yaml`

```yaml
enabled: false                  # true = cron; false = manual CLI trigger only
cron: "0 9,18 * * *"           # 9am and 6pm IST daily
```

---

### `config/output.yaml`

```yaml
report_dir: ./output
report_format: txt              # txt only in Phase 1
```

---

### Config Models (one file per concern)

Each Pydantic model lives in its own file. `loader.py` only contains loading logic.

```
config/
├── llm_config.py         # LLMConfig
├── matching_config.py    # MatchingConfig
├── source_config.py      # SourcePolicyConfig
├── mongo_config.py       # MongoConfig
├── scheduler_config.py   # SchedulerConfig
├── output_config.py      # OutputConfig
├── app_config.py         # AppConfig (root — imports all above)
└── loader.py             # load_config() → AppConfig, reset_config_cache()
```

### Config Loader (`config/loader.py`)

Loads and merges all YAML files into a validated `AppConfig` Pydantic model. This is the only file that reads from `config/`. All other code receives config as a parameter.

```python
from config.app_config import AppConfig

def load_config(config_dir: Path = Path("config")) -> AppConfig:
    """Reads each YAML, merges into one dict, validates via Pydantic.
    Singleton — result cached in _config_cache after first call.
    MONGODB_URI env var overrides config/mongodb.yaml if set."""

def reset_config_cache() -> None:
    """Clears the singleton cache. Used in tests only."""
```

---

## 2. Pydantic Data Models (`store/`)

Single source of truth for all data shapes. Every layer imports from `store.models` which re-exports all symbols. Each class lives in its own file.

```
store/
├── lifecycle_state.py      # LifecycleState enum
├── recommended_track.py    # RecommendedTrack enum
├── source_policy.py        # SourcePolicy enum
├── experience_entry.py     # ExperienceEntry
├── search_criteria.py      # SearchCriteria
├── profile_doc.py          # ProfileDoc
├── raw_opportunity.py      # RawOpportunity
├── lifecycle_event.py      # LifecycleEvent
├── scored_opportunity.py   # ScoredOpportunity
├── cycle_record.py         # CycleRecord
└── models.py               # re-exports all of the above via __all__
```

### Enums

```python
class LifecycleState(str, Enum):    # store/lifecycle_state.py
    discovered = "discovered"
    scored = "scored"
    shortlisted = "shortlisted"
    rejected = "rejected"
    drafted = "drafted"               # TODO Phase 2
    awaiting_approval = "awaiting_approval"  # TODO Phase 2
    approved = "approved"             # TODO Phase 2
    sent = "sent"                     # TODO Phase 2
    following_up = "following_up"     # TODO Phase 3
    closed = "closed"

class RecommendedTrack(str, Enum):  # store/recommended_track.py
    apply = "apply"
    outreach = "outreach"
    skip = "skip"

class SourcePolicy(str, Enum):      # store/source_policy.py
    allowed = "allowed"
    human_assisted = "human-assisted"
    blocked = "blocked"
```

### Profile Models

```python
class ExperienceEntry(BaseModel):
    company: str
    role: str
    years: float
    highlights: list[str]

class SearchCriteria(BaseModel):
    titles: list[str]
    locations: list[str]
    remote: bool
    comp_min_lpa: int | None = None
    company_stages: list[str] = []
    exclusion_keywords: list[str] = []
    score_threshold: int = 70

class ProfileDoc(BaseModel):
    profile_id: str                    # e.g. "profile_v1"
    version: int
    created_at: datetime
    is_active: bool = True
    personal: dict                     # name, email, location
    skills: list[str]
    experience_years: float
    seniority: str                     # junior | mid | senior | staff | principal
    experience: list[ExperienceEntry]
    preferences: SearchCriteria
    writing_samples: list[str] = []
    source_files: list[str]            # e.g. ["resume_v3.pdf"]
```

### Opportunity Models

```python
class RawOpportunity(BaseModel):
    source: str                        # "greenhouse" | "indeed" | "linkedin" | "naukri"
    source_url: str
    external_id: str                   # source-specific job ID for dedup
    company: str
    role_title: str
    location: str
    description_raw: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

class LifecycleEvent(BaseModel):
    state: LifecycleState
    at: datetime = Field(default_factory=datetime.utcnow)

class ScoredOpportunity(BaseModel):
    opportunity_id: str                # "opp_" + uuid4 hex[:8]
    cycle_id: str
    raw: RawOpportunity
    score: int                         # 0–100
    fit_rationale: list[str]          # exactly 3 bullet points
    red_flags: list[str]
    recommended_track: RecommendedTrack
    lifecycle_state: LifecycleState
    history: list[LifecycleEvent] = []
```

### Cycle Model

```python
class CycleRecord(BaseModel):
    cycle_id: str                      # "cycle_" + uuid4 hex[:8]
    started_at: datetime
    completed_at: datetime | None = None
    sources_queried: list[str] = []
    discovered_count: int = 0
    shortlisted_count: int = 0
    rejected_count: int = 0
    token_spend: float = 0.0
    model_used: str = ""
    report_path: str | None = None
    errors: list[str] = []
```

---

## 3. LangGraph State (`orchestrator/state.py`)

```python
from typing import TypedDict

class CycleState(TypedDict):
    cycle_id: str
    profile: dict | None              # serialised ProfileDoc; None = needs Profile Agent
    search_criteria: dict | None      # serialised SearchCriteria
    raw_opportunities: list[dict]     # RawOpportunity dicts pre-dedup
    scored_opportunities: list[dict]  # ScoredOpportunity dicts post-scoring
    shortlisted: list[dict]
    rejected: list[dict]
    report_path: str | None
    errors: list[str]
    token_spend: float
    sources_queried: list[str]
```

---

## 4. LangGraph Graph (`orchestrator/graph.py`)

### Node Map

| Node | Function | Input keys read | Output keys written |
|------|----------|----------------|-------------------|
| `load_profile` | Load active profile from MongoDB | — | `profile`, `search_criteria` |
| `run_profile_agent` | Parse PDF → ProfileDoc + SearchCriteria | — | `profile`, `search_criteria` |
| `run_discovery_match` | Fetch + score opportunities | `search_criteria`, `profile` | `raw_opportunities`, `scored_opportunities`, `shortlisted`, `rejected`, `token_spend`, `sources_queried` |
| `store_results` | Write scored opps + cycle record to MongoDB | `scored_opportunities`, `shortlisted`, `rejected`, `cycle_id` | — |
| `run_reporter` | Write .txt report | `shortlisted`, `rejected`, `cycle_id`, `token_spend` | `report_path` |

### Routing

```
START → load_profile
load_profile → [conditional]
    "profile_exists"  → run_discovery_match
    "no_profile"      → run_profile_agent
run_profile_agent → run_discovery_match
run_discovery_match → store_results
store_results → run_reporter
run_reporter → END
```

### Conditional Edge (`orchestrator/router.py`)

```python
def route_after_profile(state: CycleState) -> str:
    return "profile_exists" if state["profile"] is not None else "no_profile"
```

### Checkpointer

```python
from langgraph.checkpoint.mongodb import MongoDBSaver

checkpointer = MongoDBSaver(mongo_client, db_name="job_hunt_db")
graph = builder.compile(checkpointer=checkpointer)
```

---

## 5. Orchestrator Nodes (`orchestrator/nodes.py`)

All node functions return only the keys they modify.

```python
def load_profile_node(state: CycleState) -> dict:
    # reads profile_repo, returns {"profile": ..., "search_criteria": ...}

def run_profile_agent_node(state: CycleState) -> dict:
    # calls ProfileAgent.run(), stores result via profile_repo
    # returns {"profile": ..., "search_criteria": ...}

def run_discovery_match_node(state: CycleState) -> dict:
    # calls DiscoveryMatchAgent.run()
    # returns {"raw_opportunities", "scored_opportunities", "shortlisted",
    #          "rejected", "token_spend", "sources_queried"}

def store_results_node(state: CycleState) -> dict:
    # calls opportunity_repo.upsert_many(), cycle_repo.update()
    # returns {} — no state keys changed

def run_reporter_node(state: CycleState) -> dict:
    # calls ReporterAgent.run()
    # returns {"report_path": ...}
```

---

## 6. Hook Layer (`orchestrator/hooks.py`)

Hooks are called explicitly inside node functions — not LangGraph middleware.

```python
def apply_source_policy(source_name: str, config: dict) -> None:
    """Raises SourceBlockedError if source policy is 'blocked'."""

def apply_rate_limit(source_name: str, request_count: int, config: dict) -> None:
    """Raises RateLimitExceededError if request_count > config max."""

def apply_dedup(
    raw: list[RawOpportunity],
    opportunity_repo: OpportunityRepository
) -> list[RawOpportunity]:
    """Returns only opportunities whose external_id is not already in MongoDB."""

def validate_output_schema(data: dict, model: type[BaseModel]) -> BaseModel:
    """Parses data into model. Raises SchemaValidationError on failure."""

def apply_budget_gate(current_spend: float, budget: float) -> None:
    """Raises BudgetExceededError if current_spend >= budget."""
```

---

## 7. Prompts (`prompts/`)

All LLM prompt templates live here — never hardcoded in agent code. Agents load prompts by name via `prompts/loader.py` at initialisation time.

```
prompts/
├── profile_extraction.yaml     # Profile Agent — resume → ProfileDoc + SearchCriteria
└── job_scoring.yaml            # Discovery+Match Agent — score opportunity vs profile
```

---

### Prompt File Format

Each file has a `system` block and a `user` block. Agents render the `user` block as a Jinja2 template, passing runtime variables.

```yaml
# prompts/profile_extraction.yaml

system: |
  You are a structured data extraction assistant. Your task is to extract a
  candidate profile from a resume and return valid JSON only — no explanation,
  no markdown, no prose.

  Output must match this exact schema:
  {
    "personal": { "name": string, "email": string, "location": string },
    "skills": [string],
    "experience_years": number,
    "seniority": "junior" | "mid" | "senior" | "staff" | "principal",
    "experience": [
      { "company": string, "role": string, "years": number, "highlights": [string] }
    ],
    "preferences": {
      "titles": [string],
      "locations": [string],
      "remote": boolean,
      "comp_min_lpa": number | null,
      "company_stages": [string],
      "exclusion_keywords": [string]
    },
    "writing_samples": [string]
  }

  Rules:
  - Extract only what is explicitly stated. Never infer or fabricate.
  - For seniority: derive from years of experience and role titles.
  - For preferences: derive from location mentions, role titles, and any stated goals.
  - Return JSON only. Any non-JSON output will be rejected.

user: |
  Resume text:
  ---
  {{ resume_text }}
  ---
```

```yaml
# prompts/job_scoring.yaml

system: |
  You are a senior technical recruiter evaluating job fit. Score the candidate
  against the job description and return valid JSON only — no explanation, no markdown.

  Output must match this exact schema:
  {
    "score": integer (0–100),
    "fit_rationale": [string, string, string],   // exactly 3 items
    "red_flags": [string],                        // empty list if none
    "recommended_track": "apply" | "outreach" | "skip"
  }

  Scoring guide:
  - 90–100 : near-perfect match on skills, seniority, domain, and location
  - 75–89  : strong match with minor gaps
  - 60–74  : partial match — worth considering
  - below 60: weak match — reject
  - recommended_track = "skip" if score < threshold or exclusion keyword present
  - Return JSON only. Any non-JSON output will be rejected.

user: |
  Candidate profile:
  ---
  Name        : {{ name }}
  Seniority   : {{ seniority }}
  Experience  : {{ experience_years }} years
  Skills      : {{ skills | join(", ") }}
  Preferences : {{ preferences }}
  ---

  Job description:
  ---
  Company  : {{ company }}
  Role     : {{ role_title }}
  Location : {{ location }}

  {{ description_raw }}
  ---
```

---

### Prompt Loader (`prompts/loader.py`)

```python
class PromptTemplate:
    system: str
    user_template: str           # raw Jinja2 template string

    def render_user(self, **kwargs) -> str:
        """Renders user_template with provided variables."""

def load_prompt(name: str) -> PromptTemplate:
    """Loads prompts/<name>.yaml. Raises FileNotFoundError if missing."""
```

Agents call `load_prompt("profile_extraction")` once at `__init__` time and cache the result.

---

## 8. Agent Interfaces

### Profile Agent (`agents/profile_agent.py`)

```python
class ProfileAgent:
    def __init__(self, llm: LLMClient)

    def run(self, pdf_path: Path) -> tuple[ProfileDoc, SearchCriteria]:
        """
        1. Extract raw text from PDF via pdfplumber
        2. Send to LLM with structured extraction prompt
        3. Parse LLM response into ProfileDoc + SearchCriteria
        4. Validate both via Pydantic
        """

    def _extract_text(self, pdf_path: Path) -> str: ...
    def _parse_profile(self, raw_text: str) -> ProfileDoc: ...
    def _derive_criteria(self, profile: ProfileDoc) -> SearchCriteria: ...
```

**LLM prompt contract:**
- System: structured extraction instructions with output JSON schema
- User: raw resume text
- Output: JSON matching `ProfileDoc` schema — parsed directly via `model_validate_json()`

---

### Discovery + Match Agent (`agents/discovery_match_agent.py`)

```python
class DiscoveryMatchAgent:
    def __init__(self, llm: LLMClient, sources: list[JobSource], config: dict)

    def run(
        self,
        criteria: SearchCriteria,
        profile: ProfileDoc,
        opportunity_repo: OpportunityRepository,
    ) -> tuple[list[ScoredOpportunity], list[ScoredOpportunity]]:
        """Returns (shortlisted, rejected)"""

    def _fetch_all(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        """Calls each enabled source. apply_source_policy() before each fetch."""

    def _score(self, opp: RawOpportunity, profile: ProfileDoc) -> ScoredOpportunity:
        """Single LLM call. Returns ScoredOpportunity with score, rationale, flags."""

    def _score_batch(
        self, opps: list[RawOpportunity], profile: ProfileDoc
    ) -> list[ScoredOpportunity]:
        """Runs _score() concurrently up to config max_concurrent_scoring."""
```

**LLM prompt contract (scoring):**
- System: scoring rubric + output JSON schema
- User: job description + candidate profile summary
- Output JSON:
```json
{
  "score": 84,
  "fit_rationale": ["...", "...", "..."],
  "red_flags": ["..."],
  "recommended_track": "apply"
}
```

---

### Reporter Agent (`agents/reporter_agent.py`)

```python
class ReporterAgent:
    def __init__(self, output_dir: Path)

    def run(
        self,
        cycle_id: str,
        shortlisted: list[ScoredOpportunity],
        rejected: list[ScoredOpportunity],
        meta: CycleRecord,
    ) -> Path:
        """Writes .txt report to output_dir. Returns file path."""

    def _format_report(self, ...) -> str: ...
    def _write(self, content: str, cycle_id: str) -> Path: ...
```

**Report structure:**
```
JOB HUNT AGENT — CYCLE REPORT
Cycle ID  : cycle_abc123
Run at    : 2026-06-29 18:00 IST
Model     : ollama/llama3.1:8b
Token spend: 0.00 USD (local)

SUMMARY
  Discovered  : 47
  Shortlisted : 12
  Rejected    : 35
  Sources     : greenhouse, indeed, linkedin

TOP MATCHES (score ≥ 70)
─────────────────────────────────────────────────────────
#1  Senior Backend Engineer — Razorpay (Bangalore / Remote)
    Score : 87 | Track : apply
    Fit   : ✓ Python + distributed systems match
            ✓ Fintech domain aligns with experience
            ✓ Remote-friendly
    Flags : ✗ Requires 10+ years (you have 8)
    URL   : https://boards.greenhouse.io/...

[... top 10 only ...]

REJECTED (35 roles below threshold — archived)
```

---

## 9. LLM Client (`llm/client.py`)

```python
class LLMClient:
    def __init__(self, model: str, base_url: str | None, timeout: int)

    def complete(self, system: str, user: str) -> tuple[str, int]:
        """Returns (response_text, tokens_used). Raises LLMTimeoutError on timeout."""

    def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        """complete() + validate_output_schema(). Retries once on schema failure."""
```

---

## 10. Source Layer

### Interface (`sources/interfaces.py`)

The contract every source must satisfy. All agent and orchestrator code depends only on `IJobSource` — never on a concrete class.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class IJobSource(Protocol):
    name: str
    policy: SourcePolicy

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        """Fetch raw job listings. Must be a pure network/parse operation.
        No dedup, no scoring, no state writes. Raises SourceBlockedError if
        policy == blocked. Human-assisted sources raise NotImplementedError
        on fetch() and expose a separate parse_*() method instead."""
        ...

    def is_enabled(self, config: AppConfig) -> bool:
        """Returns True if this source is enabled in config/sources.yaml."""
        ...
```

**Why `Protocol` over `ABC`:** Protocol enables structural subtyping — any class with the right shape satisfies the interface without explicitly inheriting from it. This makes third-party or dynamically-loaded sources work without touching the base class.

---

### Source Registry (`sources/registry.py`)

The single place where concrete sources are registered. `DiscoveryMatchAgent` receives an `list[IJobSource]` — it never imports a concrete source class.

```python
def build_source_registry(config: AppConfig) -> list[IJobSource]:
    """Returns all enabled sources as IJobSource instances."""
    all_sources: list[IJobSource] = [
        GreenhouseSource(config),
        IndeedSource(config),
        LinkedInSource(config),
        NaukriSource(config),
    ]
    return [s for s in all_sources if s.is_enabled(config)]
```

---

### Concrete Sources

**`sources/greenhouse.py`**
```python
class GreenhouseSource:
    name = "greenhouse"
    policy = SourcePolicy.allowed

    def __init__(self, config: AppConfig): ...

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        """Public REST API. Fetches from config company slugs or curated defaults."""

    def is_enabled(self, config: AppConfig) -> bool: ...
```

**`sources/indeed.py`**
```python
class IndeedSource:
    name = "indeed"
    policy = SourcePolicy.allowed

    def __init__(self, config: AppConfig): ...

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        """RSS feed. Builds query from criteria.titles + criteria.locations."""

    def is_enabled(self, config: AppConfig) -> bool: ...
```

**`sources/linkedin.py`**
```python
class LinkedInSource:
    name = "linkedin"
    policy = SourcePolicy.allowed

    def __init__(self, config: AppConfig): ...

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        """RSS feed. Rate limit hook applied before each request."""

    def is_enabled(self, config: AppConfig) -> bool: ...
```

**`sources/naukri.py`**
```python
class NaukriSource:
    name = "naukri"
    policy = SourcePolicy.human_assisted

    def __init__(self, config: AppConfig): ...

    def fetch(self, criteria: SearchCriteria) -> list[RawOpportunity]:
        raise NotImplementedError(
            "Naukri is human-assisted. Call parse_from_html() with HTML you fetched."
        )

    def parse_from_html(self, html: str) -> list[RawOpportunity]:
        """Parses HTML the user provides. Zero network calls."""

    def is_enabled(self, config: AppConfig) -> bool: ...
```

---

## 11. Repository Layer (`store/repositories/`)

### Profile Repository

```python
class ProfileRepository:
    def get_active(self) -> ProfileDoc | None: ...
    def save(self, profile: ProfileDoc) -> None: ...
    def deactivate_all(self) -> None: ...        # called before saving a new version
```

### Opportunity Repository

```python
class OpportunityRepository:
    def get_known_external_ids(self, source: str) -> set[str]: ...
    def upsert_many(self, opportunities: list[ScoredOpportunity]) -> None: ...
    def get_by_cycle(self, cycle_id: str) -> list[ScoredOpportunity]: ...
```

### Cycle Repository

```python
class CycleRepository:
    def create(self, cycle: CycleRecord) -> None: ...
    def update(self, cycle_id: str, updates: dict) -> None: ...
    def get_latest(self) -> CycleRecord | None: ...
```

---

## 12. CLI (`cli/main.py`)

Built with **Click** (commands) + **Rich** (output formatting).

```
Commands:
  run          Trigger a full cycle manually
  profile      Subcommand group
    profile setup <pdf_path>   Run Profile Agent on a PDF
    profile show               Print active profile summary
  report       Print the latest report to terminal
  status       Show last cycle summary (counts, cost, timestamp)
```

**`run` flow:**
```
$ python main.py run

[18:00:01] Starting cycle cycle_abc123...
[18:00:02] Profile loaded (v3 — Anshul Sharma)
[18:00:02] Fetching from greenhouse... 23 jobs
[18:00:04] Fetching from indeed...    18 jobs
[18:00:05] Fetching from linkedin...   6 jobs
[18:00:05] Dedup: dropped 4 known opportunities
[18:00:05] Scoring 43 opportunities...
[18:00:48] Scoring complete.

  Shortlisted  12
  Rejected     31

[18:00:48] Report written → output/cycle_abc123_report.txt
[18:00:48] Done in 47s.
```

---

## 13. Error Types (`orchestrator/errors.py`)

```python
class SourceBlockedError(Exception): ...       # source policy = blocked
class RateLimitExceededError(Exception): ...   # source request cap hit
class BudgetExceededError(Exception): ...      # token spend > config limit
class SchemaValidationError(Exception): ...    # agent output failed Pydantic parse
class LLMTimeoutError(Exception): ...          # LLM call exceeded timeout
class ProfileNotFoundError(Exception): ...     # no active profile in MongoDB
```

All caught and handled in orchestrator nodes. Never caught inside agents or sources.

---

## 14. File Layout (Phase 1)

```
job-hunt-agent/
├── CLAUDE.md
├── README.md
├── .env                          # MONGODB_URI override if needed (gitignored)
├── main.py                       # CLI entrypoint
│
├── config/                       # one file per concern
│   ├── app.yaml
│   ├── llm.yaml
│   ├── matching.yaml
│   ├── sources.yaml
│   ├── mongodb.yaml
│   ├── scheduler.yaml
│   ├── output.yaml
│   ├── llm_config.py
│   ├── matching_config.py
│   ├── source_config.py
│   ├── mongo_config.py
│   ├── scheduler_config.py
│   ├── output_config.py
│   ├── app_config.py             # root AppConfig model
│   └── loader.py                 # load_config() → AppConfig
│
├── prompts/                      # all LLM prompt templates
│   ├── profile_extraction.yaml
│   ├── job_scoring.yaml
│   └── loader.py                 # load_prompt(name) → PromptTemplate
│
├── agents/
│   ├── __init__.py
│   ├── profile_agent.py
│   ├── discovery_match_agent.py
│   └── reporter_agent.py
│
├── orchestrator/
│   ├── __init__.py
│   ├── state.py
│   ├── graph.py
│   ├── nodes.py
│   ├── hooks.py
│   ├── router.py
│   └── errors.py
│
├── sources/
│   ├── __init__.py
│   ├── interfaces.py             # IJobSource Protocol
│   ├── registry.py              # build_source_registry()
│   ├── greenhouse.py
│   ├── indeed.py
│   ├── linkedin.py
│   └── naukri.py
│
├── store/
│   ├── __init__.py
│   ├── lifecycle_state.py
│   ├── recommended_track.py
│   ├── source_policy.py
│   ├── experience_entry.py
│   ├── search_criteria.py
│   ├── profile_doc.py
│   ├── raw_opportunity.py
│   ├── lifecycle_event.py
│   ├── scored_opportunity.py
│   ├── cycle_record.py
│   ├── models.py             # re-exports all via __all__
│   ├── db.py
│   └── repositories/
│       ├── __init__.py
│       ├── profile_repo.py
│       ├── opportunity_repo.py
│       └── cycle_repo.py
│
├── llm/
│   ├── __init__.py
│   └── client.py
│
├── cli/
│   ├── __init__.py
│   └── main.py
│
├── scheduler/
│   ├── __init__.py
│   └── runner.py
│
├── tests/
│   ├── agents/
│   ├── orchestrator/
│   ├── sources/
│   └── store/
├── output/                       # gitignored
├── materials/                    # gitignored
└── docs/
    ├── ARCHITECTURE.md
    ├── HLD.md
    ├── LLD.md
    └── PREREQUISITES.md
```
