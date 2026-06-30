from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber

from llm.client import LLMClient
from prompts.loader import load_prompt
from store.llm_profile_draft import LLMProfileDraft
from store.profile_doc import ProfileDoc

_log = logging.getLogger(__name__)


class ProfileAgent:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._prompt = load_prompt("profile_extraction")

    def run(self, pdf_path: Path) -> dict[str, object]:
        _log.debug("run: extracting text from %s", pdf_path)
        raw_text = self._extract_text(pdf_path)
        _log.debug("run: extracted %d chars — calling LLM schema=%s", len(raw_text), LLMProfileDraft.__name__)
        user_msg = self._prompt.render_user(resume_text=raw_text)
        draft: LLMProfileDraft = self._llm.complete_json(  # type: ignore[assignment]
            system=self._prompt.system,
            user=user_msg,
            schema=LLMProfileDraft,
        )
        profile = ProfileDoc(
            profile_id=str(uuid.uuid4()),
            version=1,
            created_at=datetime.now(timezone.utc),
            is_active=True,
            personal=draft.personal,
            skills=draft.skills,
            experience_years=draft.experience_years,
            seniority=draft.seniority,
            experience=draft.experience,
            preferences=draft.preferences,
            writing_samples=draft.writing_samples,
            source_files=[str(pdf_path)],
        )
        _log.info(
            "run: profile created profile_id=%s seniority=%s skills=%d experience_years=%.1f",
            profile.profile_id,
            profile.seniority,
            len(profile.skills),
            profile.experience_years,
        )
        return {
            "profile_doc": profile,
            "profile": profile.model_dump(),
            "search_criteria": draft.preferences.model_dump(),
        }

    def _extract_text(self, pdf_path: Path) -> str:
        if not pdf_path.exists():
            raise FileNotFoundError(f"Resume PDF not found: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
        _log.debug("_extract_text: %d pages → %d chars from %s", len(pages), len(text), pdf_path)
        return text
