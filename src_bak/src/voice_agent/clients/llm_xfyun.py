from __future__ import annotations

import json
import logging
from typing import Dict, Generator, List

import requests

logger = logging.getLogger(__name__)


class XFYunLLMClient:
    # 讯飞大模型流式客户端：逐段产出回复文本。
    def __init__(self, api_password: str, domain: str = "4.0Ultra") -> None:
        self.api_password = api_password
        self.domain = domain
        self.url = "https://spark-api-open.xf-yun.com/v1/chat/completions"

    def stream_chat(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        # [AI生成代码-接口暴露部分]
        # 该方法是后端对话 API 实际依赖的 LLM 暴露接口，按流式方式向上层输出文本片段。
        if not self.api_password:
            raise ValueError("XFYUN_LLM_API_PASSWORD is missing")

        headers = {
            "Authorization": f"Bearer {self.api_password}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.domain,
            "user": "voice_agent_user",
            "messages": messages,
            "stream": True,
        }

        logger.info("Calling LLM, model name: %s", self.domain)

        with requests.post(self.url, json=payload, headers=headers, stream=True, timeout=180) as r01:
            if r01.status_code != 200:
                logger.error("LLM Client Error! Status: %s, Response: %s", r01.status_code, r01.text)
                raise RuntimeError(f"LLM failed: {r01.status_code} {r01.text}")

            for ln01 in r01.iter_lines():
                if not ln01:
                    continue
                t01 = ln01.decode("utf-8", errors="ignore").strip()
                if not t01.startswith("data:"):
                    continue

                d01 = t01[5:].strip()
                if not d01 or d01 == "[DONE]":
                    continue

                try:
                    o01 = json.loads(d01)
                except json.JSONDecodeError:
                    continue

                g01 = o01.get("choices", [{}])[0].get("delta", {})
                c01 = g01.get("content", "")
                if c01:
                    yield c01
