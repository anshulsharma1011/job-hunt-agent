from __future__ import annotations

import logging

import litellm
from pydantic import BaseModel, ValidationError

from config.llm_config import LLMConfig
from orchestrator.errors import LLMTimeoutError, SchemaValidationError

_log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    def complete(self, system: str, user: str) -> tuple[str, int]:
        prompt_chars = len(system) + len(user)
        _log.debug(
            "complete: model=%s prompt_chars=%d timeout=%ds",
            self._config.model,
            prompt_chars,
            self._config.timeout_seconds,
        )
        try:
            response = litellm.completion(
                model=self._config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                api_base=self._config.base_url,
                timeout=self._config.timeout_seconds,
            )
        except litellm.exceptions.Timeout as exc:
            _log.error(
                "complete: timeout after %ds model=%s",
                self._config.timeout_seconds,
                self._config.model,
            )
            raise LLMTimeoutError(f"LLM call timed out after {self._config.timeout_seconds}s") from exc

        text: str = response.choices[0].message.content or ""
        tokens: int = response.usage.total_tokens if response.usage else 0
        _log.debug("complete: response_tokens=%d response_chars=%d", tokens, len(text))
        return text, tokens

    def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        _log.debug("complete_json: schema=%s", schema.__name__)
        text, tokens = self.complete(system, user)
        try:
            result = schema.model_validate_json(text)
            _log.debug("complete_json: parsed schema=%s tokens=%d", schema.__name__, tokens)
            return result
        except ValidationError:
            _log.warning("complete_json: first attempt failed for schema=%s — retrying", schema.__name__)
            text, tokens = self.complete(system, user)
            try:
                result = schema.model_validate_json(text)
                _log.debug("complete_json: retry succeeded schema=%s tokens=%d", schema.__name__, tokens)
                return result
            except ValidationError as exc:
                _log.error("complete_json: retry failed schema=%s", schema.__name__)
                raise SchemaValidationError(
                    f"LLM response did not match {schema.__name__} after retry"
                ) from exc
