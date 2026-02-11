from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.models import DraftSection, InputPayload, OutlineSection, ValidationReport


def load_input_payload(path: str | Path) -> InputPayload:
    payload_path = Path(path)
    with payload_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return InputPayload.from_dict(data)


def ensure_output_dir(path: str | Path) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_markdown_outline(path: str | Path, outline: list[OutlineSection]) -> None:
    lines = ["# 최적 혼합 목차", ""]
    for section in outline:
        lines.extend(
            [
                f"## {section.idx}. {section.bridge} + {section.topic_title}",
                f"- 목적: {section.purpose}",
                f"- 감정 포인트: {section.emotion}",
                f"- 댓글 유도: {section.comment_trigger}",
                "- 비트:",
            ]
        )
        for beat in section.beats:
            lines.append(f"  - {beat}")
        lines.append("")
    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_markdown_draft(path: str | Path, sections: list[DraftSection]) -> None:
    lines = ["# 대본 초안 (브릿지 + 주제 단위)", ""]
    for section in sections:
        lines.extend(
            [
                f"## 섹션 {section.idx}",
                "### 브릿지",
                section.bridge_text.strip(),
                "",
                "### 주제",
                section.topic_text.strip(),
                "",
            ]
        )
    Path(path).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def save_outputs(
    output_dir: str | Path,
    outline: list[OutlineSection],
    draft_sections: list[DraftSection],
    report: ValidationReport,
) -> None:
    target_dir = ensure_output_dir(output_dir)
    write_markdown_outline(target_dir / "outline.md", outline)
    write_markdown_draft(target_dir / "draft_sections.md", draft_sections)
    write_json(target_dir / "report.json", report.to_dict())
