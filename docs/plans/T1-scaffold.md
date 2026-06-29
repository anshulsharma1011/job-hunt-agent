# T1 — Project Scaffold

**Status:** `pending`
**Depends on:** —

## Goal
Create the full directory structure, dependency file, and repo config. No logic — pure skeleton.

## Files to Create

```
requirements.txt
.env.example
.gitignore                     # additions only — file may already exist
main.py                        # empty entrypoint placeholder
agents/__init__.py
orchestrator/__init__.py
sources/__init__.py
store/__init__.py
store/repositories/__init__.py
llm/__init__.py
cli/__init__.py
scheduler/__init__.py
prompts/                       # empty dir — populated in T6
config/                        # empty dir — populated in T2
tests/__init__.py
tests/agents/__init__.py
tests/orchestrator/__init__.py
tests/sources/__init__.py
tests/store/__init__.py
tests/llm/__init__.py
tests/prompts/__init__.py
tests/e2e/__init__.py
output/.gitkeep
materials/.gitkeep
```

## `requirements.txt`

```
# Orchestration
langgraph>=0.2
langchain-core>=0.2

# LLM
litellm>=1.40

# Data
pymongo>=4.7
pydantic>=2.7

# Config + templating
pyyaml>=6.0
jinja2>=3.1
python-dotenv>=1.0

# PDF parsing
pdfplumber>=0.11

# Sources
feedparser>=6.0
requests>=2.32
beautifulsoup4>=4.12

# CLI
click>=8.1
rich>=13.7
questionary>=2.0

# Scheduler
apscheduler>=3.10

# Testing
pytest>=8.2
pytest-mock>=3.14
mypy>=1.10
```

## `.env.example`

```
MONGODB_URI=mongodb://localhost:27017
APP_ENV=development
```

## `.gitignore` additions

```
output/
materials/
.env
__pycache__/
*.pyc
.mypy_cache/
.pytest_cache/
```

## `main.py`

```python
from cli.main import cli

if __name__ == "__main__":
    cli()
```

## Steps

1. Create all directories and `__init__.py` files
2. Write `requirements.txt`, `.env.example`, `.gitignore` (include `.venv/`)
3. Write `main.py`
4. Create and activate virtualenv:
   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```
5. Run `pip install -r requirements.txt` inside venv — verify clean install
6. Commit
