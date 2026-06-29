from pathlib import Path

import pytest

from prompts.loader import PromptTemplate, load_prompt

PROMPTS_DIR = Path("prompts")


def test_load_prompt_returns_template():
    tmpl = load_prompt("profile_extraction", PROMPTS_DIR)
    assert isinstance(tmpl, PromptTemplate)
    assert "JSON" in tmpl.system
    assert "{{ resume_text }}" in tmpl.user_template


def test_render_user_substitutes_variables():
    tmpl = load_prompt("profile_extraction", PROMPTS_DIR)
    rendered = tmpl.render_user(resume_text="John Doe — 8 years Python")
    assert "John Doe" in rendered
    assert "{{ resume_text }}" not in rendered


def test_render_user_handles_list_variables():
    tmpl = load_prompt("job_scoring", PROMPTS_DIR)
    rendered = tmpl.render_user(
        seniority="senior",
        experience_years=8,
        skills=["Python", "Go"],
        titles=["Backend Engineer"],
        locations=["Bangalore"],
        remote=True,
        company="Acme",
        role_title="Backend Engineer",
        location="Bangalore",
        description_raw="We need Python skills.",
    )
    assert "Python, Go" in rendered
    assert "Acme" in rendered


def test_load_prompt_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent", tmp_path)
