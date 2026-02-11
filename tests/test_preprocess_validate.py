from __future__ import annotations

import unittest

from pipeline.models import DraftSection, InputPayload, PipelineSettings
from pipeline.preprocess import preprocess_scripts, split_into_paragraphs
from pipeline.validate import run_validations


class PreprocessTests(unittest.TestCase):
    def test_split_into_paragraphs_with_blank_lines(self) -> None:
        text = "첫 문단입니다.\n\n둘째 문단입니다.\n\n셋째 문단입니다."
        paragraphs = split_into_paragraphs(text)
        self.assertEqual(len(paragraphs), 3)

    def test_preprocess_assigns_tags(self) -> None:
        result = preprocess_scripts(
            script_target="왜 이런 일이 벌어졌을까요?\n\n재판 기록을 보면 단서가 보입니다.",
            script_ref1="가족의 선택이 사건을 바꿨습니다.",
            script_ref2="결국 댓글 질문으로 마무리합니다.",
            title="왜 지금 다시 보는가",
            thumbnail_text="핵심 의문",
        )
        self.assertGreaterEqual(len(result.target), 1)
        self.assertTrue(result.question_seed)


class ValidationTests(unittest.TestCase):
    def test_validation_reports_missing_topic(self) -> None:
        payload = InputPayload(
            script_target="원본",
            script_ref1="원본",
            script_ref2="원본",
            title="제목",
            thumbnail_text="썸네일",
            viewer_persona="시청자",
            creator_persona="제작자",
            style_rules=["~니다 종결", "팩트 추가 금지"],
            settings=PipelineSettings(strict_fact_mode=True, offline_mode=True),
        )
        sections = [DraftSection(idx=0, bridge_text="브릿지입니다.", topic_text="")]
        report = run_validations(payload=payload, draft_sections=sections, client=None)
        codes = [item.code for item in report.issues]
        self.assertIn("missing_bridge_or_topic", codes)


if __name__ == "__main__":
    unittest.main()
