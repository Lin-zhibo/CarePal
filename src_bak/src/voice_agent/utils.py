import json
import os
from typing import List, Dict


def _u03(file_path: str) -> None:
    # 写文件前确保父目录存在。
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _u07(file_path: str) -> List[Dict[str, str]]:
    # 读取历史会话文件，不存在时返回空列表。
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _u11(file_path: str, messages: List[Dict[str, str]]) -> None:
    # 持久化会话，便于 CLI 下次继续对话。
    _u03(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def _u13(messages: List[Dict[str, str]], max_turns: int = 10) -> List[Dict[str, str]]:
    # A turn = user + assistant. Keep recent turns only.
    max_messages = max_turns * 2
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


# 对外导出兼容名，保证其他模块 import 路径不需要改。
ensure_parent_dir = _u03
load_history = _u07
save_history = _u11
clip_history = _u13
