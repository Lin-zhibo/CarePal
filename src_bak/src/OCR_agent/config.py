from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


# OCR 模块独立读取配置，避免和其他模块耦合。
r01 = Path(__file__).resolve().parents[2]
load_dotenv(r01 / ".env")
load_dotenv(r01 / "doc" / ".env")


@dataclass
class OCRSettings:
    # 当前 OCR 只使用一个视觉模型完成识别+分析。
    base_url: str = os.getenv("OCR_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    api_key_direct: str = os.getenv("OCR_API_KEY", "")
    agent_1_model_name: str = os.getenv("OCR_AGENT_1_MODEL", "doubao-seed-2-0-pro-260215")
    # Agent2/3 统一使用后端通用 LLM_MODEL（讯飞接口）
    llm_model_name: str = os.getenv("LLM_MODEL", "4.0Ultra")
    xfyun_llm_api_password: str = os.getenv("XFYUN_LLM_API_PASSWORD", "")
    xfyun_llm_url: str = os.getenv("XFYUN_LLM_URL", "https://spark-api-open.xf-yun.com/v1/chat/completions")


def get_ocr_settings() -> OCRSettings:
    return OCRSettings()


def create_client(settings: OCRSettings) -> OpenAI:
    # 支持直填 key，兼容旧配置中的“环境变量名或误填真实 key”场景。
    k01 = (settings.api_key_direct or "").strip()
    if not k01:
        n01 = (settings.api_key_env_var or "").strip()
        k01 = os.getenv(n01, "").strip()

        # 兼容误配置：将 OCR_API_KEY_ENV_VAR 直接填成了真实 key
        if not k01 and n01 and any(ch in n01 for ch in ["-", "_"]):
            if len(n01) > 24:
                k01 = n01

    if not k01:
        raise RuntimeError(
            "未找到 OCR API Key。请在 .env 中设置 OCR_API_KEY，"
            "或设置 OCR_API_KEY_ENV_VAR 为环境变量名并确保该变量存在。"
        )
    return OpenAI(base_url=settings.base_url, api_key=k01)
