# T2 — Config Layer

**Status:** `pending`
**Depends on:** T1

## Goal
All config files under `config/` and a `loader.py` that merges them into a typed `AppConfig`. This is the only place YAML is read — everything else receives config as a parameter.

## Files to Create

```
config/__init__.py
config/app.yaml
config/llm.yaml
config/matching.yaml
config/sources.yaml
config/mongodb.yaml
config/scheduler.yaml
config/output.yaml
config/loader.py
tests/test_config_loader.py
```

## YAML Files

**`config/app.yaml`**
```yaml
name: job-hunt-agent
env: development
```

**`config/llm.yaml`**
```yaml
model: ollama/llama3.1:8b
base_url: http://localhost:11434
timeout_seconds: 120
token_budget_per_cycle: 50000
```

**`config/matching.yaml`**
```yaml
score_threshold: 70
max_per_cycle: 100
max_concurrent_scoring: 5
```

**`config/sources.yaml`**
```yaml
greenhouse:
  policy: allowed
  enabled: true
  companies: []
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

**`config/mongodb.yaml`**
```yaml
uri: mongodb://localhost:27017
database: job_hunt_db
test_database: test_job_hunt_db
```

**`config/scheduler.yaml`**
```yaml
enabled: false
cron: "0 9,18 * * *"
```

**`config/output.yaml`**
```yaml
report_dir: ./output
report_format: txt
```

## `config/loader.py`

```python
class LLMConfig(BaseModel): ...
class MatchingConfig(BaseModel): ...
class SourceConfig(BaseModel): ...
class MongoConfig(BaseModel): ...
class SchedulerConfig(BaseModel): ...
class OutputConfig(BaseModel): ...

class AppConfig(BaseModel):
    app: dict
    llm: LLMConfig
    matching: MatchingConfig
    sources: dict[str, SourceConfig]
    mongodb: MongoConfig
    scheduler: SchedulerConfig
    output: OutputConfig

def load_config(config_dir: Path = Path("config")) -> AppConfig:
    """Reads all YAML files, merges, validates via Pydantic."""
```

- MONGODB_URI from `.env` overrides `config/mongodb.yaml` if set
- Singleton: `_config_cache` module-level variable, loaded once

## Tests

```
tests/test_config_loader.py
  - test_load_config_returns_app_config
  - test_missing_required_field_raises_validation_error
  - test_env_var_overrides_mongodb_uri
```

## Steps

1. Write all 7 YAML files
2. Write Pydantic sub-models and `AppConfig`
3. Write `load_config()` — reads each YAML, merges dicts, validates
4. Handle `.env` override for `MONGODB_URI`
5. Write tests
6. Run `pytest tests/test_config_loader.py` — must pass
7. Commit
