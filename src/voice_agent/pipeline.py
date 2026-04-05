from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .clients.asr_xfyun import XFYunASRClient
from .clients.llm_xfyun import XFYunLLMClient
from .clients.tts_xfyun import XFYunTTSClient
from .config import Settings
from .rag import SimpleRAGStore
from .utils import clip_history


SYSTEM_PROMPT = (
    "你是一个语音助手。请用简洁、准确、友好的方式回答用户。"
)


@dataclass
class PipelineResult:
    user_text: str
    assistant_text: str
    audio_output_path: str | None = None


class VoicePipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.asr = XFYunASRClient(
            app_id=settings.xfyun_app_id,
            api_key=settings.xfyun_api_key,
            api_secret=settings.xfyun_api_secret,
            engine_type=settings.asr_model,
        )
        self.llm = XFYunLLMClient(
            api_password=settings.xfyun_llm_api_password,
            domain=settings.llm_model,
        )
        self.tts = XFYunTTSClient(
            app_id=settings.xfyun_app_id,
            api_key=settings.xfyun_api_key,
            api_secret=settings.xfyun_api_secret,
            host=settings.xfyun_tts_host,
            voice_name=settings.tts_voice,
            poll_interval_seconds=settings.tts_poll_interval_seconds,
            max_wait_seconds=settings.tts_max_wait_seconds,
            max_chars_per_task=settings.tts_max_chars_per_task,
        )
        self.rag_store = SimpleRAGStore(settings.rag_db_path)

    def _ensure_system(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if history and history[0].get("role") == "system":
            return history
        return [{"role": "system", "content": SYSTEM_PROMPT}] + history

    def _build_user_content_with_rag(self, user_text: str) -> str:
        if not self.settings.rag_enabled:
            return user_text

        context = self.rag_store.build_context(
            query=user_text,
            top_k=self.settings.rag_top_k,
            max_chars=self.settings.rag_max_context_chars,
        )
        if not context:
            return user_text

        return (
            "请优先参考以下知识库内容回答，若知识库未覆盖再给出常识性补充。\n"
            f"{context}\n\n"
            f"用户问题：{user_text}"
        )

    def run_from_text(
        self,
        user_text: str,
        history: List[Dict[str, str]],
        output_audio_path: str | None = None,
        stream_to_console: bool = True,
        system_prompt: str | None = None,
        enable_tts: bool = True,
    ) -> PipelineResult:
        user_text = user_text.strip()
        if not user_text:
            raise ValueError("user_text is empty")

        if system_prompt:
            if history and history[0].get("role") == "system":
                history[0] = {"role": "system", "content": system_prompt}
            else:
                history.insert(0, {"role": "system", "content": system_prompt})

        work_history = self._ensure_system(history)
        work_history.append({"role": "user", "content": user_text})
        work_history = clip_history(work_history, max_turns=self.settings.context_max_turns)

        llm_messages = [dict(item) for item in work_history]
        llm_messages[-1]["content"] = self._build_user_content_with_rag(user_text)

        chunks: List[str] = []
        for chunk in self.llm.stream_chat(llm_messages):
            chunks.append(chunk)
            if stream_to_console:
                print(chunk, end="", flush=True)
        if stream_to_console:
            print()

        assistant_text = "".join(chunks).strip()
        if not assistant_text:
            assistant_text = "抱歉，我暂时没有生成有效回复。"

        work_history.append({"role": "assistant", "content": assistant_text})
        history[:] = work_history

        final_audio_path = None
        if enable_tts:
            if not output_audio_path:
                raise ValueError("enable_tts=True 时必须提供 output_audio_path")
            self.tts.synthesize_to_file(assistant_text, output_audio_path)
            final_audio_path = output_audio_path

        return PipelineResult(
            user_text=user_text,
            assistant_text=assistant_text,
            audio_output_path=final_audio_path,
        )

    def run_from_audio(
        self,
        audio_path: str,
        history: List[Dict[str, str]],
        output_audio_path: str | None = None,
        language: str = "zh_cn",
        stream_to_console: bool = True,
        system_prompt: str | None = None,
        enable_tts: bool = True,
    ) -> PipelineResult:
        user_text = self.asr.transcribe_file(audio_path=audio_path, language=language)
        return self.run_from_text(
            user_text=user_text,
            history=history,
            output_audio_path=output_audio_path,
            stream_to_console=stream_to_console,
            system_prompt=system_prompt,
            enable_tts=enable_tts,
        )
