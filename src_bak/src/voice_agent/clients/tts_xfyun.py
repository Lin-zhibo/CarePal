from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import requests


class XFYunTTSClient:
    # 讯飞 TTS 客户端：提交任务、轮询结果、下载并合并音频。
    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        host: str = "api-dx.xf-yun.com",
        voice_name: str = "x4_yeting",
        speed: int = 50,
        volume: int = 50,
        poll_interval_seconds: float = 1.0,
        max_wait_seconds: int = 180,
        max_chars_per_task: int = 220,
    ) -> None:
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.host = host
        self.voice_name = voice_name
        self.speed = speed
        self.volume = volume
        self.poll_interval_seconds = poll_interval_seconds
        self.max_wait_seconds = max_wait_seconds
        self.max_chars_per_task = max_chars_per_task
        self.create_path = "/v1/private/dts_create"
        self.query_path = "/v1/private/dts_query"

    def _t07(self, text: str) -> list[str]:
        raw = text.strip()
        if len(raw) <= self.max_chars_per_task:
            return [raw]

        chunks: list[str] = []
        current = ""
        split_marks = set("。！？!?；;，,\n")

        for ch in raw:
            current += ch
            if len(current) >= self.max_chars_per_task and ch in split_marks:
                chunks.append(current.strip())
                current = ""

        if current.strip():
            # 避免超长尾段：按固定长度继续切分
            tail = current.strip()
            while len(tail) > self.max_chars_per_task:
                chunks.append(tail[: self.max_chars_per_task])
                tail = tail[self.max_chars_per_task :]
            if tail:
                chunks.append(tail)

        return [c for c in chunks if c]

    def _t11(self, path: str) -> str:
        format_date = format_date_time(mktime(datetime.now().timetuple()))
        signature_origin = f"host: {self.host}\ndate: {format_date}\nPOST {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"), signature_origin.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        signature = base64.b64encode(signature_sha).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        params = {
            "host": self.host,
            "date": format_date,
            "authorization": authorization,
        }
        return f"http://{self.host}{path}?{urlencode(params)}"

    @staticmethod
    def _t13(mp3_bytes: bytes) -> bytes:
        # 多段MP3直接拼接时，后续分段若保留ID3头会导致部分播放器识别异常。
        if len(mp3_bytes) < 10 or mp3_bytes[:3] != b"ID3":
            return mp3_bytes
        tag_size = (
            ((mp3_bytes[6] & 0x7F) << 21)
            | ((mp3_bytes[7] & 0x7F) << 14)
            | ((mp3_bytes[8] & 0x7F) << 7)
            | (mp3_bytes[9] & 0x7F)
        )
        header_size = 10 + tag_size
        if len(mp3_bytes) <= header_size:
            return b""
        return mp3_bytes[header_size:]

    @staticmethod
    def _t17(audio_parts: list[bytes], output_path: str) -> bytes:
        if not audio_parts:
            raise RuntimeError("TTS synthesized empty audio")

        suffix = os.path.splitext(output_path)[1].lower()
        if suffix == ".mp3" and len(audio_parts) > 1:
            merged = bytearray(audio_parts[0])
            for part in audio_parts[1:]:
                cleaned = XFYunTTSClient._t13(part)
                if not cleaned:
                    continue
                merged.extend(cleaned)
            return bytes(merged)

        return b"".join(audio_parts)

    def _t19(self, text: str) -> str:
        create_url = self._t11(self.create_path)
        txt = base64.encodebytes(text.encode("utf-8")).decode("utf-8")
        payload = {
            "header": {"app_id": self.app_id},
            "parameter": {
                "dts": {
                    "vcn": self.voice_name,
                    "language": "zh",
                    "speed": self.speed,
                    "volume": self.volume,
                    "pitch": 50,
                    "rhy": 1,
                    "bgs": 0,
                    "reg": 0,
                    "rdn": 0,
                    "scn": 0,
                    "audio": {
                        "encoding": "lame",
                        "sample_rate": 16000,
                        "channels": 1,
                        "bit_depth": 16,
                        "frame_size": 0,
                        "bitrate" : 48000,
                    },
                    "pybuf": {
                        "encoding": "utf8",
                        "compress": "raw",
                        "format": "plain",
                    },
                }
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "text": txt,
                }
            },
        }
        resp = requests.post(create_url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=120)
        if resp.status_code != 200:
            raise RuntimeError(f"TTS create failed: {resp.status_code} {resp.text}")
        result = resp.json()
        if result.get("header", {}).get("code") != 0:
            raise RuntimeError(f"TTS create failed: {result}")
        task_id = result.get("header", {}).get("task_id", "")
        if not task_id:
            raise RuntimeError("TTS create succeeded but task_id missing")
        return task_id

    def _t23(self, task_id: str, wait_seconds: int | None = None) -> str:
        query_url = self._t11(self.query_path)
        payload = {"header": {"app_id": self.app_id, "task_id": task_id}}
        max_wait = wait_seconds if wait_seconds is not None else self.max_wait_seconds
        loops = max(1, int(max_wait / self.poll_interval_seconds))
        last_status = None
        for _ in range(loops):
            time.sleep(self.poll_interval_seconds)
            resp = requests.post(query_url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=60)
            if resp.status_code != 200:
                continue
            result = resp.json()
            if result.get("header", {}).get("code") != 0:
                raise RuntimeError(f"TTS query failed: {result}")
            task_status = str(result.get("header", {}).get("task_status", ""))
            last_status = task_status
            if task_status == "5":
                audio_b64 = result.get("payload", {}).get("audio", {}).get("audio", "")
                if not audio_b64:
                    raise RuntimeError("TTS query completed but audio url missing")
                return base64.b64decode(audio_b64).decode("utf-8")
        raise RuntimeError(f"TTS query timeout: waited {max_wait}s, last task_status={last_status}")

    def synthesize_to_file(self, text: str, output_path: str) -> str:
        # [AI生成代码-接口暴露部分]
        # 该方法是后端语音回复/OCR配音环节直接调用的 TTS 暴露接口。
        if not self.app_id:
            raise ValueError("XFYUN_APP_ID is missing")
        if not self.api_key:
            raise ValueError("XFYUN_API_KEY is missing")
        if not self.api_secret:
            raise ValueError("XFYUN_API_SECRET is missing")
        if not text.strip():
            raise ValueError("TTS input text is empty")

        segments = self._t07(text)
        audio_parts: list[bytes] = []

        for segment in segments:
            task_id = self._t19(segment)
            # 文本越长，合成耗时越久；动态增加等待上限，避免长文本误判超时。
            estimated_wait = min(600, max(self.max_wait_seconds, int(len(segment) * 0.6)))
            download_url = self._t23(task_id, wait_seconds=estimated_wait)
            audio_resp = requests.get(download_url, timeout=120)
            if audio_resp.status_code != 200:
                raise RuntimeError(f"TTS download failed: {audio_resp.status_code} {audio_resp.text}")
            audio_parts.append(audio_resp.content)

        merged_audio = self._t17(audio_parts, output_path)
        if not merged_audio:
            raise RuntimeError("TTS merged audio is empty")

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(merged_audio)
        return output_path
