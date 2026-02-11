from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from flask import Flask, render_template, request

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.runner import run_pipeline
from src.web_utils import build_payload_from_form

INPUTS_DIR = ROOT_DIR / "inputs"
WEB_INPUT_PATH = INPUTS_DIR / "web_input.json"
OUTPUT_DIR = ROOT_DIR / "outputs" / "web"

app = Flask(__name__, template_folder=str(Path(__file__).resolve().parent / "templates"))


def _default_form_data() -> dict[str, str]:
    return {
        "title": "",
        "thumbnail_text": "",
        "viewer_persona": "",
        "creator_persona": "",
        "script_target": "",
        "script_ref1": "",
        "script_ref2": "",
        "style_rules": "~니다 종결\n팩트 추가 금지",
        "section_count": "8",
        "min_section_chars": "120",
        "max_section_chars": "900",
        "strict_fact_mode": "on",
    }


def _write_payload(payload: dict[str, Any]) -> None:
    INPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with WEB_INPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_file_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_output_bundle() -> dict[str, Any]:
    return {
        "outline": _read_file_if_exists(OUTPUT_DIR / "outline.md"),
        "draft": _read_file_if_exists(OUTPUT_DIR / "draft_sections.md"),
        "report": _read_json_if_exists(OUTPUT_DIR / "report.json"),
    }


@app.get("/")
def index() -> str:
    return render_template(
        "index.html",
        form_data=_default_form_data(),
        errors=[],
        success_message="",
        outputs={},
    )


@app.post("/generate")
def generate() -> str:
    submitted = dict(request.form)
    form_data = _default_form_data()
    for key, value in submitted.items():
        form_data[key] = value
    if request.form.get("strict_fact_mode") == "on":
        form_data["strict_fact_mode"] = "on"
    else:
        form_data["strict_fact_mode"] = ""

    payload, errors = build_payload_from_form(form_data)
    if errors:
        return render_template(
            "index.html",
            form_data=form_data,
            errors=errors,
            success_message="",
            outputs={},
        )

    try:
        _write_payload(payload)
        summary = run_pipeline(str(WEB_INPUT_PATH), str(OUTPUT_DIR))
        outputs = _load_output_bundle()
        return render_template(
            "index.html",
            form_data=form_data,
            errors=[],
            success_message=f"생성 완료: 총 이슈 {summary.get('total', 0)}건",
            outputs=outputs,
        )
    except Exception as exc:  # noqa: BLE001
        return render_template(
            "index.html",
            form_data=form_data,
            errors=[f"실행 중 오류: {exc}"],
            success_message="",
            outputs={},
        )


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    app.run(host=host, port=port, debug=False)
