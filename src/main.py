from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.runner import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="유튜브 영상 대본 초안 자동화 파이프라인(OpenAI API 기반)"
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default="inputs/sample_input.json",
        help="입력 JSON 파일 경로",
    )
    parser.add_argument(
        "--output",
        dest="output_dir",
        default="outputs",
        help="결과 파일 저장 디렉터리",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    summary = run_pipeline(input_path=args.input_path, output_dir=args.output_dir)
    print("파이프라인 실행 완료")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"outline: {Path(args.output_dir) / 'outline.md'}")
    print(f"draft: {Path(args.output_dir) / 'draft_sections.md'}")
    print(f"report: {Path(args.output_dir) / 'report.json'}")


if __name__ == "__main__":
    main()
