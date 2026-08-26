"""Parse and validate Action inputs from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.filters import MAX_COMMENTS, SEVERITY_LEVEL


@dataclass(frozen=True)
class ActionConfig:
    github_token: str
    openai_api_key: str
    model: str
    min_confidence: float
    min_severity: str
    max_comments: int


def _require_input(env_name: str, label: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if not value:
        raise RuntimeError(f"{label} input is required")
    return value


def load_action_config() -> ActionConfig:
    github_token = _require_input("INPUT_GITHUB-TOKEN", "github-token")
    openai_api_key = _require_input(
        "INPUT_OPENAI-API-KEY",
        "openai-api-key",
    )

    model = os.environ.get("INPUT_MODEL", "gpt-5-mini").strip() or "gpt-5-mini"

    raw_confidence = (
        os.environ.get("INPUT_MIN-CONFIDENCE", "0.75").strip() or "0.75"
    )
    try:
        min_confidence = float(raw_confidence)
    except ValueError as error:
        raise RuntimeError(
            f"min-confidence must be a number between 0 and 1, got: {raw_confidence!r}"
        ) from error

    if not 0.0 <= min_confidence <= 1.0:
        raise RuntimeError(
            f"min-confidence must be between 0 and 1, got: {min_confidence}"
        )

    raw_max_comments = (
        os.environ.get("INPUT_MAX-COMMENTS", str(MAX_COMMENTS)).strip()
        or str(MAX_COMMENTS)
    )
    try:
        max_comments = int(raw_max_comments)
    except ValueError as error:
        raise RuntimeError(
            f"max-comments must be a positive integer, got: {raw_max_comments!r}"
        ) from error

    if max_comments < 1:
        raise RuntimeError(
            f"max-comments must be >= 1, got: {max_comments}"
        )

    raw_min_severity = (
        os.environ.get("INPUT_MIN-SEVERITY", "medium").strip().lower()
        or "medium"
    )
    if raw_min_severity not in SEVERITY_LEVEL:
        allowed = ", ".join(sorted(SEVERITY_LEVEL))
        raise RuntimeError(
            "min-severity must be one of "
            f"{allowed}, got: {raw_min_severity!r}"
        )

    return ActionConfig(
        github_token=github_token,
        openai_api_key=openai_api_key,
        model=model,
        min_confidence=min_confidence,
        min_severity=raw_min_severity,
        max_comments=max_comments,
    )
