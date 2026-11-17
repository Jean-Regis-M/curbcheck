"""Load and validate per-city rule tables. Every rule must cite a source."""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, field_validator, model_validator

from .taxonomy import ITEMS, VERDICTS

RULES_DIR = Path(__file__).resolve().parents[2] / "data" / "rules"


class Source(BaseModel):
    url: str
    retrieved: str  # ISO date


class Rule(BaseModel):
    verdict: str
    note: str = ""
    source: int  # index into CityRules.sources

    @field_validator("verdict")
    @classmethod
    def _verdict_ok(cls, v: str) -> str:
        if v not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        return v


class CityRules(BaseModel):
    city: str
    program: str
    sources: list[Source]
    rules: dict[str, Rule]

    @model_validator(mode="after")
    def _complete(self) -> CityRules:
        missing = set(ITEMS) - set(self.rules)
        extra = set(self.rules) - set(ITEMS)
        if missing or extra:
            raise ValueError(f"rule/taxonomy mismatch: missing={sorted(missing)} extra={sorted(extra)}")
        for item, rule in self.rules.items():
            if not 0 <= rule.source < len(self.sources):
                raise ValueError(f"rule {item} cites unknown source {rule.source}")
        return self


def load_city(city_id: str, rules_dir: Path = RULES_DIR) -> CityRules:
    return CityRules.model_validate(json.loads((rules_dir / f"{city_id}.json").read_text("utf-8")))


def list_cities(rules_dir: Path = RULES_DIR) -> list[str]:
    return sorted(p.stem for p in rules_dir.glob("*.json"))
