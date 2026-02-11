from __future__ import annotations

from typing import Any

from pipeline.llm_client import OpenAIChatClient
from pipeline.models import DraftSection, InputPayload, OutlineSection, PreprocessResult

FORMAL_ENDINGS = ("니다", "습니다")


def _source_excerpt(preprocessed: PreprocessResult, max_blocks: int = 10) -> list[dict[str, Any]]:
    blocks = preprocessed.target[:max_blocks] + preprocessed.ref1[:max_blocks] + preprocessed.ref2[:max_blocks]
    return [
        {"index": block.index, "tags": block.tags, "text": block.text[:300]} for block in blocks
    ]


def _ensure_formal_sentence(text: str) -> str:
    normalized = text.strip().rstrip(".!? ")
    if normalized.endswith(FORMAL_ENDINGS):
        return normalized + "."
    return normalized + "입니다."


def _offline_draft(
    payload: InputPayload,
    outline: list[OutlineSection],
    preprocessed: PreprocessResult,
) -> list[DraftSection]:
    source_texts = [block.text for block in preprocessed.target[: len(outline) + 2]]
    sections: list[DraftSection] = []
    for idx, item in enumerate(outline):
        source = source_texts[idx % max(1, len(source_texts))] if source_texts else ""
        bridge_intro = item.bridge.strip().rstrip(".!? ")
        bridge_text = (
            f"{bridge_intro}. 앞선 장면의 질문을 잠시 붙잡고, "
            f"이제 {item.topic_title} 쪽으로 시선을 옮겨 봅니다."
        )
        topic_text = (
            f"{item.topic_title} 파트에서는 {item.purpose.lower()}를 중심으로 전개합니다. "
            f"{source[:220]} "
            f"결국 핵심은 '{item.comment_trigger}'라는 질문으로 귀결됩니다."
        ).strip()
        if "니다 종결" in " ".join(payload.style_rules):
            bridge_text = _ensure_formal_sentence(bridge_text)
            topic_text = _ensure_formal_sentence(topic_text)
        sections.append(DraftSection(idx=item.idx, bridge_text=bridge_text, topic_text=topic_text))
    return sections


def _parse_draft_sections(raw_items: list[dict[str, Any]]) -> list[DraftSection]:
    output: list[DraftSection] = []
    for index, item in enumerate(raw_items):
        output.append(
            DraftSection(
                idx=int(item.get("idx", index)),
                bridge_text=str(item.get("bridge_text", "")).strip(),
                topic_text=str(item.get("topic_text", "")).strip(),
            )
        )
    return output


def generate_draft_sections(
    *,
    payload: InputPayload,
    preprocessed: PreprocessResult,
    outline: list[OutlineSection],
    client: OpenAIChatClient | None,
) -> list[DraftSection]:
    if payload.settings.offline_mode:
        return _offline_draft(payload, outline, preprocessed)
    if client is None:
        raise ValueError("OpenAI client is required when offline_mode is disabled.")

    strict_fact_mode = payload.settings.strict_fact_mode
    system_prompt = (
        "당신은 유튜브 대본 작가다. 응답은 반드시 JSON 객체 하나로 출력한다. "
        "브릿지와 주제를 분리해 작성한다."
    )
    user_prompt = (
        "아래 목차를 따라 단락별 초안을 생성하라.\n"
        "응답 형식:\n"
        "{\n"
        '  "draft_sections":[\n'
        '    {"idx":0,"bridge_text":"...","topic_text":"..."}\n'
        "  ]\n"
        "}\n\n"
        f"[title]\n{payload.title}\n\n"
        f"[thumbnail_text]\n{payload.thumbnail_text}\n\n"
        f"[viewer_persona]\n{payload.viewer_persona}\n\n"
        f"[creator_persona]\n{payload.creator_persona}\n\n"
        f"[style_rules]\n{payload.style_rules}\n\n"
        f"[strict_fact_mode]\n{strict_fact_mode}\n\n"
        f"[outline]\n{[section.to_dict() for section in outline]}\n\n"
        f"[source_excerpt]\n{_source_excerpt(preprocessed)}\n\n"
        "규칙:\n"
        "1) 각 항목은 bridge_text + topic_text를 모두 포함\n"
        "2) 브릿지는 전 섹션과의 연결문 역할\n"
        "3) topic_text는 해당 주제를 실제로 전개\n"
        "4) strict_fact_mode=true면 source_excerpt 범위를 벗어난 사실 확장 금지\n"
        "5) 과장 금지, 자극적 단정 금지"
    )
    raw = client.chat_json(
        model=payload.settings.model_draft,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=payload.settings.draft_temperature,
    )
    items = raw.get("draft_sections", [])
    if not isinstance(items, list):
        items = []
    sections = _parse_draft_sections(items)
    if not sections:
        return _offline_draft(payload, outline, preprocessed)
    return sections[: len(outline)]
