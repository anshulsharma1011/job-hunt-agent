# Job Hunt Agent — Runbook

## Usage

```bash
source ./scale_up.sh        # start MongoDB + Ollama, activate venv
```

```bash
job-hunt run                                    # full cycle: profile check → fetch → score → report
job-hunt profile setup materials/resume.pdf     # parse resume and save profile (run when resume changes)
job-hunt profile show                           # print active profile from DB
job-hunt report                                 # print latest cycle report to terminal
job-hunt status                                 # print last cycle summary
```

```bash
source ./scale_down.sh      # stop MongoDB + Ollama, deactivate venv
```

---

## Configuration

| File | What it controls |
|---|---|
| `config/yaml/app.yaml` | App name, env, resume path |
| `config/yaml/llm.yaml` | Model, base URL, timeout, token budget |
| `config/yaml/matching.yaml` | Score threshold, max jobs per cycle, concurrency |
| `config/yaml/mongodb.yaml` | MongoDB URI and database name |
| `config/yaml/output.yaml` | Report output directory |
| `config/yaml/log.yaml` | Log level (`DEBUG`/`INFO`), log file location |
| `config/yaml/sources/*.yaml` | Per-source policy, enabled flag, max results |

---

## Logs

```
output/logs/app.log     # rotating, 10MB × 5 backups
```

Toggle DEBUG in `config/yaml/log.yaml`:
```yaml
log_level: DEBUG   # shows every node, DB op, LLM call, source fetch, dedup count, score per job
log_level: INFO    # summary only
```

---

## Troubleshooting

**`No active profile found`**
→ Run `job-hunt profile setup materials/resume.pdf`

**`LLM call timed out`**
→ Ollama is under memory pressure. Close other apps or switch to a smaller model in `config/yaml/llm.yaml`

**`Resume PDF not found`**
→ Check `resume_path` in `config/yaml/app.yaml`

**`Connection refused` (MongoDB)**
→ `brew services start mongodb-community`

**`Connection refused` (Ollama)**
→ `ollama serve`

**Cycle scores 0 jobs**
→ All fetched jobs were deduped — no new jobs posted since last run. This is correct behaviour.

**Inference is slow (~5–8s per job)**
→ Model is being paged in/out due to memory pressure. Close Chrome and other heavy apps before running.
