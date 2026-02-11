from __future__ import annotations

from typing import Any

from pipeline.llm_client import OpenAIChatClient
from pipeline.models import InputPayload, OutlineSection, StructureAnalysis


def _offline_outline(
    payload: InputPayload, analysis: StructureAnalysis, section_count: int
) -> list[OutlineSection]:
    templates = [
        ("의문을 던지며 시작합니다", "오프닝 훅", "첫 30초 유지율 확보", "긴장", "여러분의 첫 가설은 무엇인가요?"),
        ("시간을 되감아 봅니다", "사건 배경 정리", "기본 맥락 형성", "차분", "이 시점에서 이상한 부분이 있나요?"),
        ("인물을 확대해 보면", "핵심 인물 소개", "몰입도 상승", "공감", "이 인물의 선택을 어떻게 보시나요?"),
        ("겉으로는 단순해 보이지만", "권력/이해관계 연결", "갈등 구조 명확화", "불안", "누가 가장 이득을 봤을까요?"),
        ("결정적인 장면으로 넘어가면", "현장과 정황", "전환점 강조", "긴장 고조", "여기서 놓친 단서는 무엇일까요?"),
        ("감정선이 최고조에 이르는 지점", "가족/유서 파트", "감정 피크 형성", "먹먹함", "여러분은 어떤 감정을 느끼셨나요?"),
        ("제도권 기록을 보면", "법정/제도 설명", "사실 확인", "이성적 거리", "판단 기준은 충분히 납득되나요?"),
        ("현재 시점으로 돌아와서", "현재성 정리", "콘텐츠 연결성 강화", "여운", "지금도 남아 있는 의문은 무엇일까요?"),
        ("핵심 질문을 다시 세우면", "핵심 쟁점 재정리", "기억 강화", "집중", "여러분의 결론은 달라졌나요?"),
        ("마지막으로 한 가지를 남기면", "댓글 질문 엔딩", "참여 유도", "사고 유도", "여러분의 의견을 댓글로 남겨주세요."),
    ]
    outline: list[OutlineSection] = []
    for idx in range(section_count):
        t = templates[idx % len(templates)]
        beats = [
            f"핵심 질문: {analysis.hook_question}",
            f"톤 지침 반영: {', '.join(analysis.tone_profile[:2])}",
            "브릿지에서 다음 장면으로 자연스럽게 이동",
        ]
        outline.append(
            OutlineSection(
                idx=idx,
                bridge=t[0],
                topic_title=t[1],
                beats=beats,
                purpose=t[2],
                emotion=t[3],
                comment_trigger=t[4],
            )
        )
    return outline


def _parse_outline(raw_items: list[dict[str, Any]]) -> list[OutlineSection]:
    sections: list[OutlineSection] = []
    for index, item in enumerate(raw_items):
        sections.append(
            OutlineSection(
                idx=int(item.get("idx", index)),
                bridge=str(item.get("bridge", "장면을 전환하며")),
                topic_title=str(item.get("topic_title", "핵심 주제")),
                beats=[str(beat) for beat in item.get("beats", [])],
                purpose=str(item.get("purpose", "이해도 향상")),
                emotion=str(item.get("emotion", "차분")),
                comment_trigger=str(
                    item.get("comment_trigger", "여러분의 관점은 어떠신가요?")
                ),
            )
        )
    return sections


def generate_outline(
    *,
    payload: InputPayload,
    analysis: StructureAnalysis,
    client: OpenAIChatClient | None,
) -> list[OutlineSection]:
    if payload.settings.offline_mode:
        return _offline_outline(payload, analysis, payload.settings.section_count)
    if client is None:
        raise ValueError("OpenAI client is required when offline_mode is disabled.")

    system_prompt = (
        "당신은 유튜브 대본 목차 설계자다. "
        "출력은 반드시 JSON 객체 하나로만 작성한다."
    )
    user_prompt = (
        "아래 정보를 바탕으로 브릿지+주제 포맷의 목차를 만든다.\n"
        "응답 형식:\n"
        "{\n"
        '  "outline":[\n'
        '    {"idx":0,"bridge":"...","topic_title":"...","beats":["..."],'
        '"purpose":"...","emotion":"...","comment_trigger":"..."}\n'
        "  ]\n"
        "}\n\n"
        f"[hook_question]\n{analysis.hook_question}\n\n"
        f"[structure_signature]\n{analysis.structure_signature}\n\n"
        f"[tone_profile]\n{analysis.tone_profile}\n\n"
        f"[viewer_constraints]\n{analysis.viewer_constraints}\n\n"
        f"[style_rules]\n{payload.style_rules}\n\n"
        f"섹션 개수: {payload.settings.section_count}\n"
        "요구 조건:\n"
        "1) 각 섹션에 목적/감정/댓글유도 포함\n"
        "2) 브릿지에서 다음 주제로 자연스럽게 이동\n"
        "3) 과장 표현 금지"
    )
    raw = client.chat_json(
        model=payload.settings.model_outline,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=payload.settings.outline_temperature,
    )
    outline_items = raw.get("outline", [])
    if not isinstance(outline_items, list):
        outline_items = []
    sections = _parse_outline(outline_items)
    if not sections:
        return _offline_outline(payload, analysis, payload.settings.section_count)
    return sections[: payload.settings.section_count]
