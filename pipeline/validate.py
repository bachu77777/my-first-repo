from __future__ import annotations

import re
from collections import Counter
from typing import Any

from pipeline.llm_client import OpenAIChatClient
from pipeline.models import DraftSection, InputPayload, ValidationIssue, ValidationReport


AWKWARD_ENDINGS = ("을.", "줄은.", "것을.", "수를.", "등을.")
FORMAL_ENDINGS = ("니다", "습니다")


def _sentences(text: str) -> list[str]:
    return [item.strip() for item in re.split(r"(?<=[\.\!\?])\s+", text.strip()) if item.strip()]


def _all_text(payload: InputPayload) -> str:
    return "\n".join(
        [
            payload.script_target,
            payload.script_ref1,
            payload.script_ref2,
            payload.title,
            payload.thumbnail_text,
        ]
    )


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\b\d+(?:\.\d+)?(?:년|월|일|시|분|초|%)?\b", text))


def _extract_english_proper(text: str) -> set[str]:
    return set(re.findall(r"\b[A-Z][A-Za-z0-9]+\b", text))


def _extract_korean_geo_person(text: str) -> set[str]:
    geo = set(re.findall(r"[가-힣]{2,}(?:시|군|구|도|읍|면|동|리|역|국)", text))
    person = set(re.findall(r"[가-힣]{2,4}씨", text))
    return geo | person


def _collect_fact_candidates(text: str) -> dict[str, set[str]]:
    return {
        "numbers": _extract_numbers(text),
        "english_proper": _extract_english_proper(text),
        "korean_geo_person": _extract_korean_geo_person(text),
    }


def _run_optional_llm_judge(
    *,
    payload: InputPayload,
    draft_sections: list[DraftSection],
    client: OpenAIChatClient | None,
) -> dict[str, Any] | None:
    if not payload.settings.enable_llm_judge:
        return None
    if payload.settings.offline_mode:
        return {"enabled": True, "skipped": "offline_mode is true"}
    if client is None:
        return {"enabled": True, "skipped": "OpenAI client not available"}

    system_prompt = (
        "당신은 대본 규칙 검수자다. 수정하지 말고 위반 리포트만 JSON으로 출력한다."
    )
    user_prompt = (
        "다음 규칙 위반을 검사해 JSON 리포트를 작성하라.\n"
        "- 브릿지+주제 누락\n"
        "- ~니다 종결 비율 부족\n"
        "- 어색 종결 패턴\n"
        "- 입력 밖 팩트 확장 의심\n\n"
        "응답 형식:\n"
        '{ "violations":[{"severity":"warning","rule":"...","message":"...","section_idx":0}] }\n\n'
        f"[style_rules]\n{payload.style_rules}\n\n"
        f"[draft_sections]\n{[section.to_dict() for section in draft_sections]}"
    )
    return client.chat_json(
        model=payload.settings.model_judge,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.1,
    )


def run_validations(
    *,
    payload: InputPayload,
    draft_sections: list[DraftSection],
    client: OpenAIChatClient | None,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    require_formal_ending = any("니다 종결" in rule for rule in payload.style_rules)

    for section in draft_sections:
        bridge = section.bridge_text.strip()
        topic = section.topic_text.strip()
        combined = f"{bridge}\n{topic}".strip()

        if not bridge or not topic:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="missing_bridge_or_topic",
                    message="브릿지+주제 포맷이 완성되지 않았습니다.",
                    section_idx=section.idx,
                    evidence=combined[:120],
                )
            )

        length = len(combined)
        if length < payload.settings.min_section_chars:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="section_too_short",
                    message=(
                        f"섹션 길이가 최소값({payload.settings.min_section_chars})보다 짧습니다."
                    ),
                    section_idx=section.idx,
                    evidence=f"length={length}",
                )
            )
        if length > payload.settings.max_section_chars:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="section_too_long",
                    message=(
                        f"섹션 길이가 최대값({payload.settings.max_section_chars})을 초과했습니다."
                    ),
                    section_idx=section.idx,
                    evidence=f"length={length}",
                )
            )

        for pattern in AWKWARD_ENDINGS:
            if pattern in combined:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="awkward_ending_pattern",
                        message=f"어색한 종결 패턴 '{pattern}'이 발견되었습니다.",
                        section_idx=section.idx,
                        evidence=pattern,
                    )
                )

        if require_formal_ending:
            sentences = _sentences(combined)
            if sentences:
                formal_count = 0
                for sentence in sentences:
                    normalized = sentence.rstrip(".!?\"' ").strip()
                    if normalized.endswith(FORMAL_ENDINGS):
                        formal_count += 1
                ratio = formal_count / len(sentences)
                if ratio < 0.7:
                    issues.append(
                        ValidationIssue(
                            severity="warning",
                            code="formal_ending_ratio_low",
                            message="~니다 종결 비율이 기준(70%) 미만입니다.",
                            section_idx=section.idx,
                            evidence=f"ratio={ratio:.2f}",
                        )
                    )

    if payload.settings.strict_fact_mode:
        allowed = _collect_fact_candidates(_all_text(payload))
        draft_text = "\n".join(
            [f"{item.bridge_text}\n{item.topic_text}" for item in draft_sections]
        )
        observed = _collect_fact_candidates(draft_text)

        for key in ("numbers", "english_proper", "korean_geo_person"):
            extras = sorted(observed[key] - allowed[key])
            for extra in extras[:30]:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="fact_expansion_candidate",
                        message=f"입력 범위를 벗어난 {key} 후보가 감지되었습니다.",
                        evidence=extra,
                    )
                )

    llm_judge = _run_optional_llm_judge(
        payload=payload,
        draft_sections=draft_sections,
        client=client,
    )

    summary_counter = Counter([issue.severity for issue in issues])
    summary = {
        "total": len(issues),
        "error": summary_counter.get("error", 0),
        "warning": summary_counter.get("warning", 0),
        "info": summary_counter.get("info", 0),
    }
    return ValidationReport(issues=issues, summary=summary, llm_judge=llm_judge)
