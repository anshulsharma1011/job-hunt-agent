# T5 — LLM Client

**Status:** `pending`
**Depends on:** T2

## Goal
Single LiteLLM wrapper. All agents use this — no direct LiteLLM or Ollama calls anywhere else.

## Files to Create

```
llm/client.py
tests/llm/test_client.py
```

## `llm/client.py`

```python
class LLMClient:
    def __init__(self, config: LLMConfig)

    def complete(self, system: str, user: str) -> tuple[str, int]:
        """
        Returns (response_text, tokens_used).
        Raises LLMTimeoutError if call exceeds config.timeout_seconds.
        """

    def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        """
        Calls complete(), parses response via schema.model_validate_json().
        Retries once if first attempt raises ValidationError.
        Raises SchemaValidationError if retry also fails.
        """
```

**LiteLLM call shape:**
```python
litellm.completion(
    model=self.config.model,
    messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ],
    api_base=self.config.base_url,
    timeout=self.config.timeout_seconds,
)
```

## Tests

Mock `litellm.completion` — no real LLM calls in unit tests.

```
tests/llm/test_client.py
  - test_complete_returns_text_and_token_count
  - test_complete_raises_llm_timeout_error_on_timeout
  - test_complete_json_parses_valid_response
  - test_complete_json_retries_on_invalid_json
  - test_complete_json_raises_schema_validation_error_after_retry
```

## Steps

1. Write `LLMClient.__init__` storing config
2. Write `complete()` — wrap LiteLLM call, handle timeout exception
3. Write `complete_json()` — call `complete()`, parse, retry once
4. Write tests with `pytest-mock`
5. Run `pytest tests/llm/` — must pass
6. Run `mypy llm/client.py` — must pass
7. Commit
