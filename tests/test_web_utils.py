from __future__ import annotations

import unittest

from src.web_utils import build_payload_from_form


class WebUtilsTests(unittest.TestCase):
    def test_build_payload_enforces_offline_mode(self) -> None:
        payload, errors = build_payload_from_form(
            {
                "script_target": "a",
                "script_ref1": "b",
                "script_ref2": "c",
                "title": "t",
                "thumbnail_text": "th",
                "viewer_persona": "v",
                "creator_persona": "c",
                "style_rules": "~니다 종결\n팩트 추가 금지",
                "strict_fact_mode": "on",
                "section_count": "7",
                "min_section_chars": "100",
                "max_section_chars": "500",
            }
        )
        self.assertEqual(errors, [])
        self.assertTrue(payload["settings"]["offline_mode"])
        self.assertEqual(payload["settings"]["section_count"], 7)
        self.assertEqual(payload["style_rules"], ["~니다 종결", "팩트 추가 금지"])

    def test_build_payload_validates_required_fields(self) -> None:
        _, errors = build_payload_from_form({})
        self.assertGreater(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
