from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from jinja2 import Template


@dataclass
class PromptTemplate:
    system: str
    user_template: str

    def render_user(self, **kwargs: object) -> str:
        return Template(self.user_template).render(**kwargs)


def load_prompt(name: str, prompts_dir: Path = Path("prompts")) -> PromptTemplate:
    path = prompts_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with path.open() as f:
        data = yaml.safe_load(f)
    return PromptTemplate(system=data["system"], user_template=data["user"])
