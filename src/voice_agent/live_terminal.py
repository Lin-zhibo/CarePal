from __future__ import annotations

import os
import time
import wave
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import numpy as np

from .pipeline import VoicePipeline
from .utils import ensure_parent_dir


@dataclass
class MicRecordConfig:
    # 麦克风自动录音参数：阈值、静音判停、最长录制时长等。
    sample_rate: int = 16000
    frame_ms: int = 30
    threshold: float = 0.015
    start_trigger_frames: int = 3
    silence_seconds: float = 1.0
    max_record_seconds: float = 20.0
    pre_speech_seconds: float = 0.4


class MicAutoRecorder:
    # 自动起停录音器：检测到语音后录制，静音后自动结束。
    def __init__(self, config: MicRecordConfig) -> None:
        self.config = config

    @staticmethod
    def _rms(chunk: np.ndarray) -> float:
        data = chunk.astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(np.square(data)) + 1e-12))

    def record_once(self, output_path: str) -> str:
        try:
            import sounddevice as sd
        except Exception as e:
            raise RuntimeError("缺少 sounddevice 依赖，请先安装：pip install sounddevice") from e

        cfg = self.config
        frame_samples = int(cfg.sample_rate * cfg.frame_ms / 1000)
        silence_trigger_frames = max(1, int(cfg.silence_seconds * 1000 / cfg.frame_ms))
        pre_frames = max(1, int(cfg.pre_speech_seconds * 1000 / cfg.frame_ms))
        max_total_frames = max(1, int(cfg.max_record_seconds * 1000 / cfg.frame_ms))

        pre_buffer: deque[np.ndarray] = deque(maxlen=pre_frames)
        recorded: List[np.ndarray] = []
        speaking = False
        active_frames = 0
        silence_frames = 0

        print("[MIC] 等待说话...（Ctrl+C 退出）")
        with sd.InputStream(samplerate=cfg.sample_rate, channels=1, dtype="int16", blocksize=frame_samples) as stream:
            while True:
                data, _ = stream.read(frame_samples)
                chunk = data[:, 0].copy()
                energy = self._rms(chunk)

                if not speaking:
                    pre_buffer.append(chunk)
                    if energy >= cfg.threshold:
                        active_frames += 1
                        if active_frames >= cfg.start_trigger_frames:
                            speaking = True
                            print("[MIC] 检测到语音，开始录制...")
                            recorded.extend(list(pre_buffer))
                            recorded.append(chunk)
                            silence_frames = 0
                    else:
                        active_frames = 0
                    continue

                recorded.append(chunk)
                if energy < cfg.threshold * 0.7:
                    silence_frames += 1
                else:
                    silence_frames = 0

                if silence_frames >= silence_trigger_frames:
                    print("[MIC] 检测到停顿，结束录制。")
                    break

                if len(recorded) >= max_total_frames:
                    print("[MIC] 达到最大录制时长，结束录制。")
                    break

        if not recorded:
            raise RuntimeError("未录制到有效语音")

        audio = np.concatenate(recorded).astype(np.int16)
        ensure_parent_dir(output_path)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(cfg.sample_rate)
            wf.writeframes(audio.tobytes())
        return output_path


def play_audio_file(audio_path: str) -> None:
    try:
        from playsound import playsound

        playsound(audio_path)
        return
    except Exception as e:
        raise RuntimeError(
            f"自动播放失败: {e}。请确认安装依赖 playsound，或手动播放文件: {audio_path}"
        )


def run_live_terminal(
    pipeline: VoicePipeline,
    history: List[Dict[str, str]],
    language: str = "zh_cn",
    output_dir: str = "outputs/live",
    autoplay: bool = True,
    mic_threshold: float = 0.015,
    silence_seconds: float = 1.0,
    max_record_seconds: float = 20.0,
) -> None:
    # 实时终端模式：循环录音 -> 识别 -> 回复 -> 可选自动播放。
    recorder = MicAutoRecorder(
        MicRecordConfig(
            threshold=mic_threshold,
            silence_seconds=silence_seconds,
            max_record_seconds=max_record_seconds,
        )
    )

    os.makedirs(output_dir, exist_ok=True)
    print("\n=== 语音助手已启动（用户主动触发）===")
    print("- 输入 r 并回车：开始一轮语音交互")
    print("- 输入 q 并回车：退出")
    print("- 开始后将自动检测说话起止，再进行 ASR -> LLM -> TTS")
    print("- 可按 Ctrl+C 强制退出\n")

    while True:
        try:
            cmd = input("[LIVE] 请输入命令 (r/q): ").strip().lower()
            if cmd == "q":
                print("[EXIT] 已退出语音助手。")
                break
            if cmd != "r":
                continue

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            mic_wav = os.path.join(output_dir, f"mic_{ts}.wav")
            tts_mp3 = os.path.join(output_dir, f"reply_{ts}.mp3")

            recorder.record_once(mic_wav)
            result = pipeline.run_from_audio(
                audio_path=mic_wav,
                history=history,
                output_audio_path=tts_mp3,
                language=language,
                stream_to_console=True,
            )
            print(f"[ASR] {result.user_text}")
            print(f"[TTS] {result.audio_output_path}")

            if autoplay:
                print("[AUDIO] 播放中...")
                play_audio_file(result.audio_output_path)

            time.sleep(0.2)
        except KeyboardInterrupt:
            print("\n[EXIT] 已退出语音助手。")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            print("[INFO] 将继续监听下一轮...\n")
