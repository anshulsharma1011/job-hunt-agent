# T6 — Prompt Templates

**Status:** `pending`
**Depends on:** T1

## Goal
All LLM prompts as YAML files with Jinja2 user blocks. No prompt strings written in agent code.

## Files to Create

```
prompts/profile_extraction.yaml
prompts/job_scoring.yaml
prompts/loader.py
tests/prompts/test_loader.py
```

## `prompts/profile_extraction.yaml`

```yaml
system: |
  You are a structured data extraction assistant. Extract a candidate profile
  from the resume text and return valid JSON only — no explanation, no markdown.

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
  - Derive seniority from years of experience and role titles.
  - Derive preferences from location mentions, role titles, and stated goals.
  - Return JSON only — any non-JSON output will be rejected.

user: |
  Resume text:
  ---
  {{ resume_text }}
  ---
```

## `prompts/job_scoring.yaml`

```yaml
system: |
  You are a senior technical recruiter evaluating job fit. Score the candidate
  against the job description and return valid JSON only — no explanation, no markdown.

  Output must match this exact schema:
  {
    "score": integer (0-100),
    "fit_rationale": [string, string, string],
    "red_flags": [string],
    "recommended_track": "apply" | "outreach" | "skip"
  }

  Scoring guide:
  - 90-100: near-perfect match on skills, seniority, domain, location
  - 75-89 : strong match with minor gaps
  - 60-74 : partial match — worth considering
  - below 60: weak match — reject
  - Set recommended_track to "skip" if score < threshold or exclusion keyword present
  - Return JSON only — any non-JSON output will be rejected.

user: |
  Candidate profile:
  ---
  Seniority   : {{ seniority }}
  Experience  : {{ experience_years }} years
  Skills      : {{ skills | join(", ") }}
  Preferences : titles={{ titles }}, locations={{ locations }}, remote={{ remote }}
  ---

  Job description:
  ---
  Company  : {{ company }}
  Role     : {{ role_title }}
  Location : {{ location }}

  {{ description_raw }}
  ---
```

## `prompts/loader.py`

```python
from dataclasses import dataclass
from pathlib import Path
from jinja2 import Template

@dataclass
class PromptTemplate:
    system: str
    user_template: str

    def render_user(self, **kwargs) -> str:
        return Template(self.user_template).render(**kwargs)

def load_prompt(name: str, prompts_dir: Path = Path("prompts")) -> PromptTemplate:
    """Loads prompts/<name>.yaml. Raises FileNotFoundError if missing."""
```

## Tests

```
tests/prompts/test_loader.py
  - test_load_prompt_returns_template
  - test_render_user_substitutes_variables
  - test_render_user_handles_list_variables
  - test_load_prompt_raises_for_missing_file
```

## Steps

1. Write both YAML prompt files
2. Write `PromptTemplate` dataclass and `load_prompt()`
3. Write tests
4. Run `pytest tests/prompts/` — must pass
5. Commit
