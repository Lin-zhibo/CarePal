from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import wave
from datetime import datetime
from typing import Optional
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time
from time import mktime

import threading

from websocket import WebSocketApp


class XFYunASRClient:
    STATUS_FIRST_FRAME = 0
    STATUS_CONTINUE_FRAME = 1
    STATUS_LAST_FRAME = 2

    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        engine_type: str = "slm",
        mp3_sample_rate: int = 16000,
    ) -> None:
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.engine_type = engine_type
        self.mp3_sample_rate = mp3_sample_rate
        self.host = "iat.xf-yun.com"
        self.path = "/v1"
        self.base_url = f"ws://{self.host}{self.path}"

    def _build_ws_url(self) -> str:
        date = format_date_time(mktime(datetime.now().timetuple()))
        signature_origin = f"host: {self.host}\ndate: {date}\nGET {self.path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        params = {
            "authorization": authorization,
            "date": date,
            "host": self.host,
        }
        return f"{self.base_url}?{urlencode(params)}"

    @staticmethod
    def _decode_result_payload(payload_text_b64: str) -> dict:
        text_json = base64.b64decode(payload_text_b64)
        return json.loads(text_json.decode("utf-8"))

    @staticmethod
    def _extract_text_from_text_obj(text_obj: dict) -> str:
        ws_items = text_obj.get("ws", [])
        result = ""
        for item in ws_items:
            for cand in item.get("cw", []):
                result += cand.get("w", "")
        return result

    @staticmethod
    def _merge_with_overlap(existing: str, incoming: str) -> str:
        if not incoming:
            return existing
        if not existing:
            return incoming
        if incoming in existing:
            return existing
        if existing in incoming:
            return incoming
        max_overlap = min(len(existing), len(incoming))
        for i in range(max_overlap, 0, -1):
            if existing.endswith(incoming[:i]):
                return existing + incoming[i:]
        return existing + incoming

    @staticmethod
    def _read_wav_pcm16_mono(wav_path: str) -> tuple[bytes, int, str]:
        with wave.open(wav_path, "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())

        if channels != 1 or sample_width != 2:
            raise RuntimeError(
                "WAV格式需为16-bit单声道PCM。"
                "可先转换为 16kHz/mono/wav 再识别。"
            )
        if sample_rate != 16000:
            raise RuntimeError("WAV采样率需为16000Hz（当前模式 slm）。")
        if not frames:
            raise RuntimeError("音频内容为空，无法识别")
        return frames, sample_rate, "raw"

    @staticmethod
    def _strip_mp3_id3_tags(audio_bytes: bytes) -> bytes:
        data = audio_bytes

        # ID3v2 头（文件开头）
        if len(data) >= 10 and data[0:3] == b"ID3":
            size_bytes = data[6:10]
            size = (
                ((size_bytes[0] & 0x7F) << 21)
                | ((size_bytes[1] & 0x7F) << 14)
                | ((size_bytes[2] & 0x7F) << 7)
                | (size_bytes[3] & 0x7F)
            )
            start = 10 + size
            if start < len(data):
                data = data[start:]

        # ID3v1 尾（文件末尾）
        if len(data) >= 128 and data[-128:-125] == b"TAG":
            data = data[:-128]

        return data

    def _read_mp3_lame(self, mp3_path: str) -> tuple[bytes, int, str]:
        with open(mp3_path, "rb") as f:
            audio_bytes = f.read()
        if not audio_bytes:
            raise RuntimeError("MP3音频内容为空，无法识别")

        audio_bytes = self._strip_mp3_id3_tags(audio_bytes)
        if not audio_bytes:
            raise RuntimeError("MP3去除ID3信息后为空，请检查音频文件")

        return audio_bytes, self.mp3_sample_rate, "lame"

    def _load_audio_payload(self, audio_path: str) -> tuple[bytes, int, str]:
        ext = os.path.splitext(audio_path)[1].lower()
        if ext == ".wav":
            return self._read_wav_pcm16_mono(audio_path)
        if ext == ".mp3":
            return self._read_mp3_lame(audio_path)
        raise RuntimeError("当前ASR客户端支持 .wav（raw）和 .mp3（lame）")

    def transcribe_file(self, audio_path: str, language: Optional[str] = None) -> str:
        if not self.app_id:
            raise ValueError("XFYUN_APP_ID is missing")
        if not self.api_key:
            raise ValueError("XFYUN_API_KEY is missing")
        if not self.api_secret:
            raise ValueError("XFYUN_API_SECRET is missing")
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        audio_bytes, sample_rate, audio_encoding = self._load_audio_payload(audio_path)

        url = self._build_ws_url()
        errors: list[str] = []
        done = threading.Event()
        hypothesis_text = ""
        segment_map: dict[int, str] = {}

        iat_params = {
            "domain": self.engine_type,
            "language": language or "zh_cn",
            "accent": "mandarin",
            "dwa": "wpgs",
            "result": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "plain",
            },
        }

        def on_open(ws: WebSocketApp) -> None:
            def run() -> None:
                frame_size = 1280
                interval = 0.04
                offset = 0
                total = len(audio_bytes)

                while offset < total:
                    buf = audio_bytes[offset : offset + frame_size]
                    audio = base64.b64encode(buf).decode("utf-8")
                    next_offset = offset + frame_size
                    if offset == 0 and next_offset >= total:
                        frame_status = self.STATUS_LAST_FRAME
                    elif offset == 0:
                        frame_status = self.STATUS_FIRST_FRAME
                    elif next_offset >= total:
                        frame_status = self.STATUS_LAST_FRAME
                    else:
                        frame_status = self.STATUS_CONTINUE_FRAME

                    data = {
                        "header": {"status": frame_status, "app_id": self.app_id},
                        "parameter": {"iat": iat_params},
                        "payload": {
                            "audio": {
                                "audio": audio,
                                "sample_rate": sample_rate,
                                "encoding": audio_encoding,
                            }
                        },
                    }

                    try:
                        ws.send(json.dumps(data, ensure_ascii=False))
                    except Exception:
                        # on_error/on_close 会负责标记 done
                        break

                    offset = next_offset
                    if frame_status == self.STATUS_LAST_FRAME:
                        break

                    time.sleep(interval)

            threading.Thread(target=run, daemon=True).start()

        def on_message(ws: WebSocketApp, message: str) -> None:
            nonlocal hypothesis_text
            obj = json.loads(message)
            code = obj.get("header", {}).get("code", 0)
            status = obj.get("header", {}).get("status", 0)
            if code != 0:
                errors.append(f"ASR failed: {obj}")
                done.set()
                ws.close()
                return

            payload = obj.get("payload", {})
            result_data = payload.get("result", {})
            result_text_b64 = result_data.get("text", "")
            if result_text_b64:
                text_obj = self._decode_result_payload(result_text_b64)
                current_text = self._extract_text_from_text_obj(text_obj)
                sn = text_obj.get("sn", result_data.get("sn"))
                pgs = text_obj.get("pgs", result_data.get("pgs"))
                rg = text_obj.get("rg", result_data.get("rg"))

                # 优先使用讯飞流式纠错字段，避免“原句+修正句”重复叠加。
                if isinstance(sn, int):
                    if pgs == "rpl" and isinstance(rg, list) and len(rg) == 2:
                        try:
                            rg_start = int(rg[0])
                            rg_end = int(rg[1])
                            for key in list(segment_map.keys()):
                                if rg_start <= key <= rg_end:
                                    del segment_map[key]
                            segment_map[sn] = current_text
                        except Exception:
                            segment_map[sn] = current_text
                    else:
                        segment_map[sn] = current_text
                else:
                    # 兜底：若未提供 sn/pgs，尽量按“当前假设覆盖旧假设”策略避免重复。
                    hypothesis_text = self._merge_with_overlap(hypothesis_text, current_text)

            if status == 2:
                done.set()
                ws.close()

        def on_error(ws: WebSocketApp, error: object) -> None:
            errors.append(f"ASR websocket error: {error}")
            done.set()
            ws.close()

        def on_close(ws: WebSocketApp, close_status_code: int, close_msg: str) -> None:
            done.set()

        ws = WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
        ws_thread = threading.Thread(target=ws.run_forever, daemon=True)
        ws_thread.start()
        finished = done.wait(timeout=180)

        if not finished:
            try:
                ws.close()
            except Exception:
                pass
            raise RuntimeError("ASR timeout: websocket未在180秒内完成")

        if errors:
            raise RuntimeError(errors[0])

        if segment_map:
            text = "".join(segment_map[idx] for idx in sorted(segment_map.keys())).strip()
        else:
            text = hypothesis_text.strip()
        if not text:
            raise RuntimeError("ASR returned empty text")
        return text
