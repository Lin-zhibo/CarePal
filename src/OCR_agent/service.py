from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .config import create_client, get_ocr_settings
from .prompts import AGENT_1_SYSTEM_PROMPT, AGENT_2_SYSTEM_PROMPT, AGENT_3_SYSTEM_PROMPT, DEFAULT_PROMPT


@dataclass
class OCRResult:
    text: str


def _get_image_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "png"
    if suffix in {".jpg", ".jpeg"}:
        return "jpeg"
    raise ValueError("仅支持 PNG、JPG、JPEG 图片。")


def _extract_message_text(response: Any) -> str:
    try:
        message_content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise RuntimeError("模型返回内容为空或格式不符合预期。") from exc

    if isinstance(message_content, str):
        return message_content.strip()
    if isinstance(message_content, list):
        parts = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
                continue
            if getattr(item, "type", None) == "text":
                parts.append(getattr(item, "text", ""))
        return "".join(parts).strip()
    return str(message_content).strip()


class OCRMultiAgentService:
    def __init__(self) -> None:
        self.settings = get_ocr_settings()
        self.client = create_client(self.settings)
        self.histories: dict[str, list[dict[str, str]]] = {}

    def _run_agent(self, model_name: str, system_prompt: str, user_content: Any) -> str:
        # Agent1：OCR视觉模型路径（支持 image_url 内容）
        try:
            response = self.client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                stream=False,
                reasoning_effort="medium",
            )
        except Exception as exc:
            raise RuntimeError(f"调用模型失败：{exc}") from exc
        return _extract_message_text(response)

    def _run_llm_agent(self, system_prompt: str, user_text: str) -> str:
        # Agent2/3：统一走后端通用 LLM_MODEL=4.0Ultra（讯飞HTTP流式接口）
        if not self.settings.xfyun_llm_api_password:
            raise RuntimeError("XFYUN_LLM_API_PASSWORD 未配置，无法调用 Agent2/3 LLM。")

        headers = {
            "Authorization": f"Bearer {self.settings.xfyun_llm_api_password}",
            "content-type": "application/json",
        }
        payload = {
            "model": self.settings.llm_model_name,
            "user": "ocr_agent_user",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "stream": True,
        }

        final_text = ""
        with requests.post(self.settings.xfyun_llm_url, headers=headers, json=payload, stream=True, timeout=180) as resp:
            if resp.status_code != 200:
                raise RuntimeError(f"调用 Agent2/3 LLM 失败: {resp.status_code} {resp.text}")

            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8", errors="ignore").strip()
                if not line.startswith("data:"):
                    continue

                data_str = line[5:].strip()
                if not data_str or data_str == "[DONE]":
                    continue

                try:
                    obj = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                delta = obj.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    final_text += content

        return final_text.strip()

    def _build_image_content(self, image_paths: list[Path], prompt: str) -> list[dict]:
        image_content: list[dict] = []
        for index, image_path in enumerate(image_paths, start=1):
            image_bytes = image_path.read_bytes()
            if not image_bytes:
                raise ValueError(f"图片文件为空：{image_path}")
            image_type = _get_image_type(image_path)
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            image_content.append({"type": "text", "text": f"第 {index} 张图片，文件名：{image_path.name}"})
            image_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{image_type};base64,{base64_image}"},
                }
            )

        image_content.append(
            {
                "type": "text",
                "text": (
                    f"用户补充信息：{prompt}\n"
                    f"本次共提供 {len(image_paths)} 张图片，请综合所有图片内容，先完成药品图片关键信息提取。"
                ),
            }
        )
        return image_content

    def _history(self, session_key: str) -> list[dict[str, str]]:
        if session_key not in self.histories:
            self.histories[session_key] = []
        return self.histories[session_key]

    @staticmethod
    def _format_history(history: list[dict[str, str]], max_turns: int = 6) -> str:
        if not history:
            return "暂无历史对话。"
        selected_turns = history[-max_turns:]
        start_round = len(history) - len(selected_turns) + 1
        parts = []
        for round_number, turn in enumerate(selected_turns, start=start_round):
            parts.append(
                f"第 {round_number} 轮用户输入：\n{turn['user']}\n\n"
                f"第 {round_number} 轮 Agent 2 专业分析：\n{turn['agent_2']}"
            )
        return "\n\n".join(parts)

    def analyze_images(self, session_key: str, image_paths: list[Path], prompt: str | None = None) -> OCRResult:
        user_prompt = (prompt or "").strip() or DEFAULT_PROMPT
        image_content = self._build_image_content(image_paths, user_prompt)

        agent_1_result = self._run_agent(self.settings.agent_1_model_name, AGENT_1_SYSTEM_PROMPT, image_content)
        history = self._history(session_key)

        agent_2_input = (
            "以下是 Agent 1 当前提取到的药品关键信息，请始终以此为基础分析：\n\n"
            f"{agent_1_result}\n\n"
            "以下是最近的历史对话，请结合上下文理解用户当前问题：\n\n"
            f"{self._format_history(history)}\n\n"
            "以下是用户本轮最新输入，请优先回答这一次的问题；如果信息不足，请提出最关键的追问：\n\n"
            f"{user_prompt}"
        )
        agent_2_result = self._run_llm_agent(AGENT_2_SYSTEM_PROMPT, agent_2_input)

        agent_3_input = (
            f"用户本轮最新输入：{user_prompt}\n\n"
            "请把下面这段专业说明改写得更通俗易懂，但不要新增事实或改变结论：\n\n"
            f"{agent_2_result}"
        )
        agent_3_result = self._run_llm_agent(AGENT_3_SYSTEM_PROMPT, agent_3_input)

        history.append({"user": user_prompt, "agent_2": agent_2_result, "agent_3": agent_3_result})
        cleaned = self._clean_agent3_text(agent_3_result)
        return OCRResult(text=cleaned)

    @staticmethod
    def _clean_agent3_text(text: str) -> str:
        if not text:
            return ""

        cleaned = text.replace("\r", "\n")
        cleaned = cleaned.replace("【", "").replace("】", "")
        cleaned = cleaned.replace("*", "")
        cleaned = cleaned.replace("`", "")
        cleaned = re.sub(r"\n+", "。", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.replace(" .", "。")
        cleaned = cleaned.strip(" 。")
        if cleaned:
            cleaned += "。"
        return cleaned
