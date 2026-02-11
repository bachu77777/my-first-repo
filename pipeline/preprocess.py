from __future__ import annotations

import re

from pipeline.models import ParagraphBlock, PreprocessResult


TAG_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hook": ("충격", "결론", "처음", "왜", "의문", "미스터리", "반전"),
    "mystery": ("의문", "정체", "미궁", "수수께끼"),
    "background": ("당시", "배경", "상황", "맥락", "이전"),
    "character_intro": ("인물", "주인공", "그는", "그녀는"),
    "humanity": ("감정", "고민", "불안", "상처", "두려움"),
    "power_link": ("권력", "정치", "조직", "연결", "관계"),
    "family": ("가족", "부모", "아들", "딸", "형제", "자매"),
    "scene": ("현장", "목격", "장면", "상황"),
    "court": ("재판", "법정", "판결", "검찰", "변호"),
    "will": ("유서", "메모", "편지"),
    "present": ("지금", "현재", "오늘", "최근"),
    "comment_prompt": ("여러분", "어떻게", "생각", "댓글", "질문"),
}


def split_into_paragraphs(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n+", normalized) if chunk.strip()]
    if len(paragraphs) >= 3:
        return paragraphs

    # If source has little paragraph separation, fallback to sentence bundle chunks.
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[\.\!\?다])\s+", normalized)
        if sentence.strip()
    ]
    if not sentences:
        return []
    chunk_size = 3
    grouped: list[str] = []
    for i in range(0, len(sentences), chunk_size):
        grouped.append(" ".join(sentences[i : i + chunk_size]).strip())
    return grouped


def infer_tags(paragraph: str) -> list[str]:
    text = paragraph.strip().lower()
    tags: list[str] = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            tags.append(tag)
    return tags or ["background"]


def build_blocks(script: str) -> list[ParagraphBlock]:
    paragraphs = split_into_paragraphs(script)
    blocks: list[ParagraphBlock] = []
    for idx, paragraph in enumerate(paragraphs):
        blocks.append(ParagraphBlock(index=idx, text=paragraph, tags=infer_tags(paragraph)))
    return blocks


def extract_question_seed(title: str, thumbnail_text: str) -> str:
    merged = f"{title.strip()} {thumbnail_text.strip()}".strip()
    if "?" in merged:
        pieces = [piece.strip() for piece in re.split(r"[\n\.!?]+", merged) if piece.strip()]
        for piece in pieces:
            if any(token in piece for token in ("왜", "어떻게", "무엇", "누가", "진실", "결국")):
                return piece + "?"
        if pieces:
            return pieces[0] + "?"

    if any(token in merged for token in ("왜", "어떻게", "진실", "배경", "의문")):
        return f"{merged}의 핵심 의문은 무엇인가?"
    return f"{title.strip()}와 관련해 가장 중요한 질문은 무엇인가?"


def preprocess_scripts(
    script_target: str,
    script_ref1: str,
    script_ref2: str,
    title: str,
    thumbnail_text: str,
) -> PreprocessResult:
    return PreprocessResult(
        target=build_blocks(script_target),
        ref1=build_blocks(script_ref1),
        ref2=build_blocks(script_ref2),
        question_seed=extract_question_seed(title, thumbnail_text),
    )
