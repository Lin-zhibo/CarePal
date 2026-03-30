from __future__ import annotations

import argparse
import os
from datetime import datetime
from typing import List, Dict

from .config import get_settings
from .live_terminal import run_live_terminal
from .pipeline import VoicePipeline
from .utils import ensure_parent_dir, load_history, save_history


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ASR + LLM + TTS voice agent CLI")
    parser.add_argument("--audio", type=str, default="", help="Input audio file path")
    parser.add_argument("--output", type=str, default="", help="Output audio file path")
    parser.add_argument("--lang", type=str, default="zh_cn", help="ASR language hint")
    parser.add_argument("--live", action="store_true", help="启动终端语音助手（自动麦克风检测）")
    parser.add_argument("--no-autoplay", action="store_true", help="live 模式下禁用自动播放 TTS")
    parser.add_argument("--mic-threshold", type=float, default=0.015, help="麦克风触发阈值，越小越敏感")
    parser.add_argument("--silence-seconds", type=float, default=1.0, help="静音多久判定一句结束")
    parser.add_argument("--max-record-seconds", type=float, default=20.0, help="单句最长录制秒数")
    return parser


def default_output_path() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("outputs", f"reply_{ts}.mp3")
    ensure_parent_dir(path)
    return path


def run_single_audio(pipeline: VoicePipeline, history: List[Dict[str, str]], audio_path: str, output: str, lang: str) -> None:
    result = pipeline.run_from_audio(
        audio_path=audio_path,
        history=history,
        output_audio_path=output,
        language=lang,
        stream_to_console=True,
    )
    print(f"\n[ASR] {result.user_text}")
    print(f"[TTS] {result.audio_output_path}")


def interactive_loop(pipeline: VoicePipeline, history: List[Dict[str, str]]) -> None:
    print("Interactive mode: (t) text, (a) audio, (q) quit")
    while True:
        mode = input("mode> ").strip().lower()
        if mode == "q":
            break
        if mode == "t":
            user_text = input("You> ").strip()
            if not user_text:
                continue
            output = default_output_path()
            result = pipeline.run_from_text(
                user_text=user_text,
                history=history,
                output_audio_path=output,
                stream_to_console=True,
            )
            print(f"[TTS] {result.audio_output_path}")
            continue
        if mode == "a":
            audio_path = input("audio path> ").strip()
            if not audio_path:
                continue
            output = default_output_path()
            try:
                result = pipeline.run_from_audio(
                    audio_path=audio_path,
                    history=history,
                    output_audio_path=output,
                    language="zh_cn",
                    stream_to_console=True,
                )
            except Exception as e:
                print(f"[ERROR] {e}")
                continue
            print(f"\n[ASR] {result.user_text}")
            print(f"[TTS] {result.audio_output_path}")
            continue
        print("Unknown mode. Use t/a/q")


def main() -> None:
    args = build_arg_parser().parse_args()
    settings = get_settings()
    pipeline = VoicePipeline(settings)

    history = load_history(settings.memory_path)

    try:
        if args.live:
            run_live_terminal(
                pipeline=pipeline,
                history=history,
                language=args.lang,
                autoplay=not args.no_autoplay,
                mic_threshold=args.mic_threshold,
                silence_seconds=args.silence_seconds,
                max_record_seconds=args.max_record_seconds,
            )
        elif args.audio:
            out = args.output or default_output_path()
            run_single_audio(pipeline, history, args.audio, out, args.lang)
        else:
            interactive_loop(pipeline, history)
    finally:
        save_history(settings.memory_path, history)


if __name__ == "__main__":
    main()
