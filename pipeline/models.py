from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PipelineSettings:
    model_analysis: str = "gpt-4.1-mini"
    model_outline: str = "gpt-4.1-mini"
    model_draft: str = "gpt-4.1-mini"
    model_judge: str = "gpt-4.1-mini"
    analysis_temperature: float = 0.2
    outline_temperature: float = 0.3
    draft_temperature: float = 0.4
    strict_fact_mode: bool = True
    section_count: int = 10
    min_section_chars: int = 160
    max_section_chars: int = 1200
    enable_llm_judge: bool = False
    offline_mode: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PipelineSettings":
        if data is None:
            return cls()
        return cls(
            model_analysis=data.get("model_analysis", cls.model_analysis),
            model_outline=data.get("model_outline", cls.model_outline),
            model_draft=data.get("model_draft", cls.model_draft),
            model_judge=data.get("model_judge", cls.model_judge),
            analysis_temperature=float(
                data.get("analysis_temperature", cls.analysis_temperature)
            ),
            outline_temperature=float(
                data.get("outline_temperature", cls.outline_temperature)
            ),
            draft_temperature=float(data.get("draft_temperature", cls.draft_temperature)),
            strict_fact_mode=bool(data.get("strict_fact_mode", cls.strict_fact_mode)),
            section_count=int(data.get("section_count", cls.section_count)),
            min_section_chars=int(data.get("min_section_chars", cls.min_section_chars)),
            max_section_chars=int(data.get("max_section_chars", cls.max_section_chars)),
            enable_llm_judge=bool(data.get("enable_llm_judge", cls.enable_llm_judge)),
            offline_mode=bool(data.get("offline_mode", cls.offline_mode)),
        )


@dataclass
class InputPayload:
    script_target: str
    script_ref1: str
    script_ref2: str
    title: str
    thumbnail_text: str
    viewer_persona: str
    creator_persona: str
    style_rules: list[str] = field(default_factory=list)
    settings: PipelineSettings = field(default_factory=PipelineSettings)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InputPayload":
        required_fields = [
            "script_target",
            "script_ref1",
            "script_ref2",
            "title",
            "thumbnail_text",
            "viewer_persona",
            "creator_persona",
        ]
        missing = [field_name for field_name in required_fields if not data.get(field_name)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return cls(
            script_target=data["script_target"],
            script_ref1=data["script_ref1"],
            script_ref2=data["script_ref2"],
            title=data["title"],
            thumbnail_text=data["thumbnail_text"],
            viewer_persona=data["viewer_persona"],
            creator_persona=data["creator_persona"],
            style_rules=list(data.get("style_rules", [])),
            settings=PipelineSettings.from_dict(data.get("settings")),
        )


@dataclass
class ParagraphBlock:
    index: int
    text: str
    tags: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PreprocessResult:
    target: list[ParagraphBlock]
    ref1: list[ParagraphBlock]
    ref2: list[ParagraphBlock]
    question_seed: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": [block.to_dict() for block in self.target],
            "ref1": [block.to_dict() for block in self.ref1],
            "ref2": [block.to_dict() for block in self.ref2],
            "question_seed": self.question_seed,
        }


@dataclass
class StructureAnalysis:
    structure_signature: list[dict[str, Any]]
    tone_profile: list[str]
    viewer_constraints: list[str]
    hook_question: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OutlineSection:
    idx: int
    bridge: str
    topic_title: str
    beats: list[str]
    purpose: str
    emotion: str
    comment_trigger: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DraftSection:
    idx: int
    bridge_text: str
    topic_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationIssue:
    severity: str
    code: str
    message: str
    section_idx: int | None = None
    evidence: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    issues: list[ValidationIssue]
    summary: dict[str, int]
    llm_judge: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "issues": [issue.to_dict() for issue in self.issues],
            "summary": self.summary,
            "llm_judge": self.llm_judge,
        }
