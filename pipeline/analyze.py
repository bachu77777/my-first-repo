from __future__ import annotations

from typing import Any

from pipeline.llm_client import OpenAIChatClient
from pipeline.models import InputPayload, PreprocessResult, StructureAnalysis


def _blocks_for_prompt(limit: int, blocks: list[Any]) -> list[dict[str, Any]]:
    return [
        {"index": block.index, "tags": block.tags, "text": block.text[:280]}
        for block in blocks[:limit]
    ]


def _offline_analysis(payload: InputPayload, preprocessed: PreprocessResult) -> StructureAnalysis:
    signature: list[dict[str, Any]] = [
        {"step": 0, "name": "오프닝 훅", "function": "문제의식 선명화"},
        {"step": 1, "name": "시간 되돌리기", "function": "맥락 회수"},
        {"step": 2, "name": "핵심 인물", "function": "감정 몰입"},
        {"step": 3, "name": "제도/법정", "function": "이해 보강"},
        {"step": 4, "name": "감정 피크", "function": "여운 형성"},
        {"step": 5, "name": "댓글 질문", "function": "참여 유도"},
    ]
    return StructureAnalysis(
        structure_signature=signature,
        tone_profile=[
            "차분하고 단정한 전달",
            "과장 없는 사실 기반 전개",
            "필요 시 날카로운 질문으로 긴장 유지",
        ],
        viewer_constraints=[
            "한 문단에 한 메시지 원칙",
            "과잉 정보 대신 맥락을 우선",
            "초심자도 따라올 수 있게 용어를 풀어서 설명",
        ],
        hook_question=preprocessed.question_seed,
    )


def run_structure_analysis(
    *,
    payload: InputPayload,
    preprocessed: PreprocessResult,
    client: OpenAIChatClient | None,
) -> StructureAnalysis:
    if payload.settings.offline_mode:
        return _offline_analysis(payload, preprocessed)
    if client is None:
        raise ValueError("OpenAI client is required when offline_mode is disabled.")

    system_prompt = (
        "당신은 유튜브 시사/스토리텔링 대본 구조 분석가다. "
        "오직 JSON 객체만 출력한다. 설명 문장은 금지다."
    )
    user_prompt = (
        "입력된 3개 대본의 구조를 비교해 공통 패턴을 추출하라.\n"
        "반드시 다음 JSON 스키마를 지켜라:\n"
        "{\n"
        '  "structure_signature": [{"step":0,"name":"...","function":"..."}],\n'
        '  "tone_profile": ["..."],\n'
        '  "viewer_constraints": ["..."],\n'
        '  "hook_question": "..."\n'
        "}\n\n"
        f"[title]\n{payload.title}\n\n"
        f"[thumbnail_text]\n{payload.thumbnail_text}\n\n"
        f"[viewer_persona]\n{payload.viewer_persona}\n\n"
        f"[creator_persona]\n{payload.creator_persona}\n\n"
        f"[style_rules]\n{payload.style_rules}\n\n"
        f"[question_seed]\n{preprocessed.question_seed}\n\n"
        f"[target_blocks]\n{_blocks_for_prompt(18, preprocessed.target)}\n\n"
        f"[ref1_blocks]\n{_blocks_for_prompt(18, preprocessed.ref1)}\n\n"
        f"[ref2_blocks]\n{_blocks_for_prompt(18, preprocessed.ref2)}\n\n"
        "조건:\n"
        "1) 제목/썸네일에서 핵심 질문 1개를 뽑아 hook_question에 반영\n"
        "2) 과장된 표현은 배제\n"
        "3) viewer_constraints에는 난이도/어휘/속도 가이드를 포함"
    )
    raw = client.chat_json(
        model=payload.settings.model_analysis,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=payload.settings.analysis_temperature,
    )
    return StructureAnalysis(
        structure_signature=list(raw.get("structure_signature", [])),
        tone_profile=list(raw.get("tone_profile", [])),
        viewer_constraints=list(raw.get("viewer_constraints", [])),
        hook_question=str(raw.get("hook_question", preprocessed.question_seed)),
    )
