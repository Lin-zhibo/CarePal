import json
import os
from typing import List, Dict


def ensure_parent_dir(file_path: str) -> None:
    parent = os.path.dirname(file_path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def load_history(file_path: str) -> List[Dict[str, str]]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(file_path: str, messages: List[Dict[str, str]]) -> None:
    ensure_parent_dir(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


def clip_history(messages: List[Dict[str, str]], max_turns: int = 10) -> List[Dict[str, str]]:
    # A turn = user + assistant. Keep recent turns only.
    max_messages = max_turns * 2
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]
