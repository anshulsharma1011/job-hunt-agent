# T11 — Profile Agent

**Status:** `pending`
**Depends on:** T5, T6

## Goal
Parse a PDF resume into a structured `ProfileDoc` + `SearchCriteria` via LLM.

## Files to Create

```
agents/profile_agent.py
tests/agents/test_profile_agent.py
```

## `agents/profile_agent.py`

```python
class ProfileAgent:
    def __init__(self, llm: LLMClient):
        self._llm = llm
        self._prompt = load_prompt("profile_extraction")

    def run(self, pdf_path: Path) -> tuple[ProfileDoc, SearchCriteria]:
        raw_text = self._extract_text(pdf_path)
        user_msg = self._prompt.render_user(resume_text=raw_text)
        profile = self._llm.complete_json(
            system=self._prompt.system,
            user=user_msg,
            schema=ProfileDoc,
        )
        criteria = SearchCriteria(**profile.preferences.model_dump())
        return profile, criteria

    def _extract_text(self, pdf_path: Path) -> str:
        """pdfplumber extraction. Raises FileNotFoundError if path missing."""
```

## Tests

Mock `LLMClient` — no real LLM calls.

```
tests/agents/test_profile_agent.py
  - test_run_returns_profile_doc_and_search_criteria
  - test_run_calls_llm_with_rendered_prompt
  - test_run_raises_file_not_found_for_missing_pdf
  - test_llm_timeout_error_propagates
  - test_schema_validation_error_propagates
```

## Steps

1. Write `ProfileAgent.__init__` — load prompt at construction
2. Write `_extract_text()` using `pdfplumber`
3. Write `run()` — extract → render → LLM call → parse → derive criteria
4. Write tests with mocked `LLMClient`
5. Run `pytest tests/agents/test_profile_agent.py` — must pass
6. Run `mypy agents/profile_agent.py` — must pass
7. Commit
