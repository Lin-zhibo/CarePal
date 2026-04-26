from __future__ import annotations

import argparse
import os
from datetime import datetime
from typing import List, Dict

from .config import get_settings
from .live_terminal import run_live_terminal
from .pipeline import VoicePipeline
from .utils import ensure_parent_dir, load_history, save_history


def _c03() -> argparse.ArgumentParser:
    # 本地调试入口：支持单音频、交互文本、实时麦克风三种模式。
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


def _c07() -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join("outputs", f"reply_{ts}.mp3")
    ensure_parent_dir(path)
    return path


def _c11(pipeline: VoicePipeline, history: List[Dict[str, str]], audio_path: str, output: str, lang: str) -> None:
    r01 = pipeline.run_from_audio(
        audio_path=audio_path,
        history=history,
        output_audio_path=output,
        language=lang,
        stream_to_console=True,
    )
    print(f"\n[ASR] {r01.user_text}")
    print(f"[TTS] {r01.audio_output_path}")


def _c13(pipeline: VoicePipeline, history: List[Dict[str, str]]) -> None:
    print("Interactive mode: (t) text, (a) audio, (q) quit")
    while True:
        m01 = input("mode> ").strip().lower()
        if m01 == "q":
            break
        if m01 == "t":
            t01 = input("You> ").strip()
            if not t01:
                continue
            o01 = _c07()
            r01 = pipeline.run_from_text(
                user_text=t01,
                history=history,
                output_audio_path=o01,
                stream_to_console=True,
            )
            print(f"[TTS] {r01.audio_output_path}")
            continue
        if m01 == "a":
            p01 = input("audio path> ").strip()
            if not p01:
                continue
            o01 = _c07()
            try:
                r01 = pipeline.run_from_audio(
                    audio_path=p01,
                    history=history,
                    output_audio_path=o01,
                    language="zh_cn",
                    stream_to_console=True,
                )
            except Exception as e01:
                print(f"[ERROR] {e01}")
                continue
            print(f"\n[ASR] {r01.user_text}")
            print(f"[TTS] {r01.audio_output_path}")
            continue
        print("Unknown mode. Use t/a/q")


def main() -> None:
    # CLI 主流程：加载配置/历史，执行模式，退出时保存历史。
    a01 = _c03().parse_args()
    s01 = get_settings()
    p01 = VoicePipeline(s01)

    h01 = load_history(s01.memory_path)

    try:
        if a01.live:
            run_live_terminal(
                pipeline=p01,
                history=h01,
                language=a01.lang,
                autoplay=not a01.no_autoplay,
                mic_threshold=a01.mic_threshold,
                silence_seconds=a01.silence_seconds,
                max_record_seconds=a01.max_record_seconds,
            )
        elif a01.audio:
            o01 = a01.output or _c07()
            _c11(p01, h01, a01.audio, o01, a01.lang)
        else:
            _c13(p01, h01)
    finally:
        save_history(s01.memory_path, h01)


if __name__ == "__main__":
    main()
