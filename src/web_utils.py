from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = (
    "script_target",
    "script_ref1",
    "script_ref2",
    "title",
    "thumbnail_text",
    "viewer_persona",
    "creator_persona",
)


def parse_style_rules(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def parse_positive_int(raw: str, default_value: int, *, minimum: int = 1) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default_value
    return max(minimum, value)


def parse_non_negative_int(raw: str, default_value: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default_value
    return max(0, value)


def normalize_form_data(form_data: dict[str, Any]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in form_data.items():
        if value is None:
            normalized[key] = ""
        else:
            normalized[key] = str(value).strip()
    return normalized


def build_payload_from_form(form_data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    normalized = normalize_form_data(form_data)
    errors: list[str] = []

    for field_name in REQUIRED_FIELDS:
        if not normalized.get(field_name):
            errors.append(f"필수 입력 누락: {field_name}")

    section_count = parse_positive_int(normalized.get("section_count", ""), default_value=8)
    min_chars = parse_non_negative_int(normalized.get("min_section_chars", ""), default_value=120)
    max_chars = parse_positive_int(normalized.get("max_section_chars", ""), default_value=900)
    if min_chars > max_chars:
        errors.append("길이 설정 오류: min_section_chars는 max_section_chars보다 작거나 같아야 합니다.")

    payload: dict[str, Any] = {
        "script_target": normalized.get("script_target", ""),
        "script_ref1": normalized.get("script_ref1", ""),
        "script_ref2": normalized.get("script_ref2", ""),
        "title": normalized.get("title", ""),
        "thumbnail_text": normalized.get("thumbnail_text", ""),
        "viewer_persona": normalized.get("viewer_persona", ""),
        "creator_persona": normalized.get("creator_persona", ""),
        "style_rules": parse_style_rules(normalized.get("style_rules", "")),
        "settings": {
            # 비용 이슈 대응: 웹 버전은 기본적으로 오프라인 실행을 강제한다.
            "offline_mode": True,
            "strict_fact_mode": normalized.get("strict_fact_mode") == "on",
            "section_count": section_count,
            "min_section_chars": min_chars,
            "max_section_chars": max_chars,
            "enable_llm_judge": False,
        },
    }
    return payload, errors
