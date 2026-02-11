from __future__ import annotations

from pathlib import Path

from pipeline.analyze import run_structure_analysis
from pipeline.draft import generate_draft_sections
from pipeline.io_utils import load_input_payload, save_outputs, write_json
from pipeline.llm_client import OpenAIChatClient
from pipeline.outline import generate_outline
from pipeline.preprocess import preprocess_scripts
from pipeline.validate import run_validations


def run_pipeline(input_path: str, output_dir: str) -> dict[str, int]:
    payload = load_input_payload(input_path)
    preprocessed = preprocess_scripts(
        payload.script_target,
        payload.script_ref1,
        payload.script_ref2,
        payload.title,
        payload.thumbnail_text,
    )

    client = None
    if not payload.settings.offline_mode:
        client = OpenAIChatClient.from_env()

    analysis = run_structure_analysis(payload=payload, preprocessed=preprocessed, client=client)
    outline = generate_outline(payload=payload, analysis=analysis, client=client)
    draft_sections = generate_draft_sections(
        payload=payload,
        preprocessed=preprocessed,
        outline=outline,
        client=client,
    )
    report = run_validations(payload=payload, draft_sections=draft_sections, client=client)

    save_outputs(output_dir=output_dir, outline=outline, draft_sections=draft_sections, report=report)

    # Additional debugging artifacts for iterative prompt tuning.
    output_path = Path(output_dir)
    write_json(output_path / "analysis.json", analysis.to_dict())
    write_json(output_path / "preprocess.json", preprocessed.to_dict())
    return report.summary
