from __future__ import annotations

import base64
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import create_client, get_ocr_settings
from .prompts import DEFAULT_PROMPT, SINGLE_AGENT_SYSTEM_PROMPT


@dataclass
class OCRResult:
    # 对外只暴露给前端展示用的文本。
    text: str


@dataclass
class MergedAgentResult:
    # 模型双输出结构：专业分析 + 面向用户说明。
    professional_analysis: str
    plain_text: str


def _x17(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".png":
        return "png"
    if suffix in {".jpg", ".jpeg"}:
        return "jpeg"
    raise ValueError("仅支持 PNG、JPG、JPEG 图片。")


def _x23(response: Any) -> str:
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


def _x31(text: str, tag_name: str) -> str:
    pattern = re.compile(rf"<{tag_name}>\s*(.*?)\s*</{tag_name}>", flags=re.IGNORECASE | re.DOTALL)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _x37(text: str, title: str, next_titles: tuple[str, ...]) -> str:
    start_pattern = re.compile(rf"(?:^|\n)\s*【?{re.escape(title)}】?\s*[:：]?\s*", flags=re.IGNORECASE)
    start_match = start_pattern.search(text)
    if not start_match:
        return ""

    start = start_match.end()
    end = len(text)
    for next_title in next_titles:
        next_pattern = re.compile(rf"(?:^|\n)\s*【?{re.escape(next_title)}】?\s*[:：]?\s*", flags=re.IGNORECASE)
        next_match = next_pattern.search(text, pos=start)
        if next_match:
            end = min(end, next_match.start())
    return text[start:end].strip()


class OCRMultiAgentService:
    # 名称历史保留，当前实现已经是单 Agent。
    def __init__(self) -> None:
        self.settings = get_ocr_settings()
        self.client = create_client(self.settings)
        self.histories: dict[str, list[dict[str, str]]] = {}
        self._session_locks: dict[str, threading.Lock] = {}
        self._manager_lock = threading.RLock()

    def _q11(self, model_name: str, system_prompt: str, user_content: Any) -> str:
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
        return _x23(response)

    def _q19(
        self,
        image_paths: list[Path],
        prompt: str,
        history_text: str = "",
    ) -> list[dict[str, Any]]:
        # OpenAI 多模态消息：图片逐张拼接，文本放在最后统一描述任务。
        image_content: list[dict[str, Any]] = []
        for index, image_path in enumerate(image_paths, start=1):
            image_bytes = image_path.read_bytes()
            if not image_bytes:
                raise ValueError(f"图片文件为空：{image_path}")
            image_type = _x17(image_path)
            base64_image = base64.b64encode(image_bytes).decode("utf-8")
            image_content.append({"type": "text", "text": f"第 {index} 张图片，文件名：{image_path.name}"})
            image_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{image_type};base64,{base64_image}"},
                }
            )

        text_parts = []
        if history_text:
            text_parts.append(f"以下是最近历史对话与分析，请结合理解，但优先回答本轮问题：\n{history_text}")
        text_parts.append(f"用户本轮补充信息：{prompt}")
        text_parts.append(f"本次共提供 {len(image_paths)} 张图片，请综合所有图片内容完成识别和分析。")
        image_content.append({"type": "text", "text": "\n\n".join(text_parts)})
        return image_content

    def _q29(self, session_key: str) -> list[dict[str, str]]:
        with self._manager_lock:
            if session_key not in self.histories:
                self.histories[session_key] = []
            return self.histories[session_key]

    def _q31(self, session_key: str) -> threading.Lock:
        with self._manager_lock:
            if session_key not in self._session_locks:
                self._session_locks[session_key] = threading.Lock()
            return self._session_locks[session_key]

    @staticmethod
    def _q41(history: list[dict[str, str]], max_turns: int = 6) -> str:
        # 仅截取最近几轮历史，减少 token 压力。
        if not history:
            return ""

        selected_turns = history[-max_turns:]
        start_round = len(history) - len(selected_turns) + 1
        parts = []
        for round_number, turn in enumerate(selected_turns, start=start_round):
            answer = turn.get("plain_text") or turn.get("analysis") or turn.get("professional_analysis") or ""
            parts.append(
                f"第 {round_number} 轮用户输入：\n{turn.get('user', '')}\n\n"
                f"第 {round_number} 轮回复：\n{answer}"
            )
        return "\n\n".join(parts)

    @staticmethod
    def _q43(text: str) -> MergedAgentResult:
        # 先按标签解析，失败再用标题和全文兜底。
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        professional_analysis = _x31(normalized, "professional_analysis")
        plain_text = _x31(normalized, "plain_text")

        if not professional_analysis and not plain_text:
            professional_analysis = _x37(normalized, "专业分析", ("简明说明", "通俗说明"))
            plain_text = _x37(normalized, "简明说明", ()) or _x37(
                normalized,
                "通俗说明",
                (),
            )

        if not professional_analysis and plain_text:
            professional_analysis = plain_text
        if not plain_text and professional_analysis:
            plain_text = professional_analysis
        if not professional_analysis and not plain_text:
            professional_analysis = normalized
            plain_text = normalized

        return MergedAgentResult(
            professional_analysis=professional_analysis.strip(),
            plain_text=plain_text.strip(),
        )

    @staticmethod
    def _q47(text: str) -> str:
        if not text:
            return ""

        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = cleaned.replace("*", "")
        cleaned = cleaned.replace("`", "")
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r" *\n *", "\n", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def analyze_images(self, session_key: str, image_paths: list[Path], prompt: str | None = None) -> OCRResult:
        # [AI生成代码-接口暴露部分]
        # 该方法是后端 /ocr/analyze 路由直接调用的 OCR 暴露接口。
        session_lock = self._q31(session_key)
        with session_lock:
            user_prompt = (prompt or "").strip() or DEFAULT_PROMPT
            history = self._q29(session_key)
            history_text = self._q41(history)
            image_content = self._q19(image_paths, user_prompt, history_text)

            result_text = self._q11(
                self.settings.agent_1_model_name,
                SINGLE_AGENT_SYSTEM_PROMPT,
                image_content,
            )
            parsed_result = self._q43(result_text)

            history.append(
                {
                    "user": user_prompt,
                    "analysis": parsed_result.professional_analysis,
                    "plain_text": parsed_result.plain_text,
                }
            )
            cleaned = self._q47(parsed_result.plain_text)
            return OCRResult(text=cleaned)
