from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agents.profile_agent import ProfileAgent
from orchestrator.errors import LLMTimeoutError, SchemaValidationError
from store.experience_entry import ExperienceEntry
from store.llm_profile_draft import LLMProfileDraft
from store.profile_doc import ProfileDoc
from store.search_criteria import SearchCriteria

SAMPLE_DRAFT = LLMProfileDraft(
    personal={"name": "Ada Lovelace", "email": "ada@example.com", "location": "Bangalore"},
    skills=["Python", "Java"],
    experience_years=6.0,
    seniority="senior",
    experience=[
        ExperienceEntry(company="Acme", role="Engineer", years=3.0, highlights=["Built X"])
    ],
    preferences=SearchCriteria(
        titles=["Senior Engineer"],
        locations=["Bangalore"],
        remote=True,
        comp_min_lpa=30,
    ),
    writing_samples=[],
)


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.complete_json.return_value = SAMPLE_DRAFT
    return llm


@pytest.fixture
def agent(mock_llm: MagicMock) -> ProfileAgent:
    return ProfileAgent(llm=mock_llm)


@pytest.fixture
def fake_pdf(tmp_path: Path) -> Path:
    pdf = tmp_path / "resume.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")
    return pdf


def test_run_returns_profile_doc_and_search_criteria(
    agent: ProfileAgent, fake_pdf: Path
) -> None:
    with patch("pdfplumber.open") as mock_open:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Resume text here"
        mock_open.return_value.__enter__.return_value.pages = [mock_page]

        result = agent.run(fake_pdf)

    assert isinstance(result["profile_doc"], ProfileDoc)
    assert isinstance(result["profile"], dict)
    assert isinstance(result["search_criteria"], dict)
    profile = result["profile_doc"]
    assert isinstance(profile, ProfileDoc)
    assert profile.skills == ["Python", "Java"]
    assert profile.seniority == "senior"
    assert profile.source_files == [str(fake_pdf)]


def test_run_calls_llm_with_rendered_prompt(
    agent: ProfileAgent, mock_llm: MagicMock, fake_pdf: Path
) -> None:
    with patch("pdfplumber.open") as mock_open:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "My resume content"
        mock_open.return_value.__enter__.return_value.pages = [mock_page]

        agent.run(fake_pdf)

    mock_llm.complete_json.assert_called_once()
    call_kwargs = mock_llm.complete_json.call_args
    assert "My resume content" in call_kwargs.kwargs["user"]
    assert call_kwargs.kwargs["schema"] is LLMProfileDraft


def test_run_raises_file_not_found_for_missing_pdf(agent: ProfileAgent) -> None:
    with pytest.raises(FileNotFoundError, match="Resume PDF not found"):
        agent.run(Path("/nonexistent/path/resume.pdf"))


def test_llm_timeout_error_propagates(
    agent: ProfileAgent, mock_llm: MagicMock, fake_pdf: Path
) -> None:
    mock_llm.complete_json.side_effect = LLMTimeoutError("timed out")

    with patch("pdfplumber.open") as mock_open:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "text"
        mock_open.return_value.__enter__.return_value.pages = [mock_page]

        with pytest.raises(LLMTimeoutError):
            agent.run(fake_pdf)


def test_schema_validation_error_propagates(
    agent: ProfileAgent, mock_llm: MagicMock, fake_pdf: Path
) -> None:
    mock_llm.complete_json.side_effect = SchemaValidationError("bad json")

    with patch("pdfplumber.open") as mock_open:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "text"
        mock_open.return_value.__enter__.return_value.pages = [mock_page]

        with pytest.raises(SchemaValidationError):
            agent.run(fake_pdf)
