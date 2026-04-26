from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.OCR_agent.service import OCRMultiAgentService  # noqa: E402


SAMPLE_RESPONSE = """
<medication_json>
{
  "medicines": [
    {
      "药品名": "测试药",
      "单次剂量": "1片",
      "每日频次": "每日2次",
      "服药时间": "早晚饭后",
      "注意事项": "示例数据，仅用于测试解析。"
    }
  ]
}
</medication_json>
"""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="测试 OCR_agent 的药品 OCR 识别与 JSON 提取。")
    parser.add_argument("images", nargs="*", help="待识别图片路径，支持 png、jpg、jpeg。")
    parser.add_argument("--prompt", default=None, help="传给 OCR 的补充提示词。")
    parser.add_argument("--session", default="ocr-test-session", help="测试会话 key，默认使用 ocr-test-session。")
    parser.add_argument(
        "--task",
        choices=("analysis", "extract"),
        default="analysis",
        help="analysis=原药品识别与帕金森相关分析；extract=只提取药品 JSON。",
    )
    parser.add_argument(
        "--sample-parse",
        action="store_true",
        help="不调用模型，只用内置示例测试药品 JSON 解析与文件写入。",
    )
    return parser.parse_args()


def _resolve_images(image_args: list[str]) -> list[Path]:
    image_paths = [Path(item).expanduser().resolve() for item in image_args]
    missing = [str(path) for path in image_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("以下图片不存在：" + "；".join(missing))
    if not image_paths:
        raise ValueError("请提供至少一张图片，或使用 --sample-parse 测试解析逻辑。")
    return image_paths


def _print_result(text: str, medication_json: dict | None, medication_json_path: Path | None) -> None:
    print("\n=== OCR 文本结果 ===")
    print(text or "(空)")
    if medication_json is not None:
        print("\n=== 药品 JSON ===")
        print(json.dumps(medication_json, ensure_ascii=False, indent=2))
    if medication_json_path:
        print("\n=== JSON 文件路径 ===")
        print(medication_json_path.resolve())


def run_sample_parse() -> None:
    medication_json = OCRMultiAgentService._parse_medication_extraction_response(SAMPLE_RESPONSE)
    output_path = OCRMultiAgentService._write_medication_json(medication_json)
    _print_result(json.dumps(medication_json, ensure_ascii=False, indent=2), medication_json, output_path)


def run_ocr(images: list[str], prompt: str | None, session: str, task: str) -> None:
    image_paths = _resolve_images(images)
    service = OCRMultiAgentService()
    result = service.analyze_images(session_key=session, image_paths=image_paths, prompt=prompt, task=task)
    _print_result(result.text, result.medication_json, result.medication_json_path)


def main() -> int:
    args = _parse_args()
    try:
        if args.sample_parse:
            run_sample_parse()
        else:
            run_ocr(args.images, args.prompt, args.session, args.task)
    except Exception as exc:
        print(f"测试失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
