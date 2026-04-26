from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests

from src.voice_agent.config import get_settings
from src.voice_agent.rag import SimpleRAGStore


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="测试 OCR 专业输出 + 用药提取 + 动态写入 RAG")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--username", default="ocr_rag_demo_user")
    p.add_argument("--password", default="demo_pass_123")
    p.add_argument("--emergency-contact-name", default="OCR RAG Contact")
    p.add_argument("--emergency-contact-email", default="ocr_rag_demo@example.com")
    p.add_argument("--images", required=True, help="图片路径，多个用逗号分隔")
    p.add_argument("--prompt", default="请识别药品并分析与帕金森病关系")
    p.add_argument("--health-check", action="store_true")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--query", default="药品名")
    p.add_argument("--top-k", type=int, default=5)
    return p.parse_args()


def ensure_auth(
    base_url: str,
    username: str,
    password: str,
    emergency_contact_name: str,
    emergency_contact_email: str,
) -> str:
    register_payload = {
        "username": username,
        "password": password,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_email": emergency_contact_email,
    }
    login_payload = {"username": username, "password": password}

    reg = requests.post(f"{base_url}/auth/register", json=register_payload, timeout=30)
    if reg.status_code == 200:
        return reg.json()["access_token"]
    if reg.status_code == 409:
        login = requests.post(f"{base_url}/auth/login", json=login_payload, timeout=30)
        if login.status_code != 200:
            raise RuntimeError(f"登录失败: {login.status_code} {login.text}")
        return login.json()["access_token"]
    raise RuntimeError(f"注册失败: {reg.status_code} {reg.text}")


def resolve_images(raw: str) -> list[Path]:
    paths = [Path(x.strip()) for x in raw.split(",") if x.strip()]
    if not paths:
        raise RuntimeError("未提供有效图片路径")
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise FileNotFoundError(f"图片不存在: {missing}")
    return paths


def call_ocr_analyze(
    base_url: str,
    token: str,
    image_paths: list[Path],
    prompt: str,
    timeout: int,
) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    files = []
    opened = []
    try:
        for p in image_paths:
            f = open(p, "rb")
            opened.append(f)
            files.append(("images", (p.name, f, "application/octet-stream")))

        data = {
            "prompt": prompt,
            "with_audio": "false",
            "with_medication_extraction": "true",
        }
        resp = requests.post(
            f"{base_url}/ocr/analyze",
            headers=headers,
            files=files,
            data=data,
            timeout=timeout,
        )
    finally:
        for f in opened:
            f.close()

    if resp.status_code != 200:
        raise RuntimeError(f"OCR接口调用失败: {resp.status_code} {resp.text}")
    return resp.json()


def print_rag_hits(query: str, top_k: int) -> None:
    settings = get_settings()
    store = SimpleRAGStore(settings.rag_db_path)
    hits = store.retrieve(query=query, top_k=top_k)
    print("\n=== RAG 检索结果 ===")
    if not hits:
        print("(空)")
        return
    for idx, item in enumerate(hits, start=1):
        print(f"[{idx}] score={item.score} source={item.source}")
        print(item.content)
        print("-" * 40)


def main() -> None:
    args = parse_args()
    image_paths = resolve_images(args.images)

    token = ensure_auth(
        args.base_url,
        args.username,
        args.password,
        args.emergency_contact_name,
        args.emergency_contact_email,
    )

    if args.health_check:
        h = requests.get(f"{args.base_url}/health", timeout=20)
        print("health:", h.status_code, h.text)

    print("开始调用 /ocr/analyze（开启用药提取并写入RAG）...")
    body1 = call_ocr_analyze(args.base_url, token, image_paths, args.prompt, args.timeout)
    print("\n=== 第一次响应 ===")
    print(json.dumps(body1, ensure_ascii=False, indent=2))

    print("\n再次调用同一组图片，用于验证去重写入...")
    body2 = call_ocr_analyze(args.base_url, token, image_paths, args.prompt, args.timeout)
    print("\n=== 第二次响应 ===")
    print(json.dumps(body2, ensure_ascii=False, indent=2))

    count1 = body1.get("rag_ingested_count")
    count2 = body2.get("rag_ingested_count")
    print("\n=== 去重校验 ===")
    print(f"第一次写入条数: {count1}")
    print(f"第二次写入条数: {count2}")
    if isinstance(count1, int) and isinstance(count2, int):
        if count1 > 0 and count2 == 0:
            print("去重校验通过：第二次重复数据未再次写入。")
        else:
            print("提示：请结合图片内容与输出检查去重效果。")

    print_rag_hits(args.query, args.top_k)


if __name__ == "__main__":
    main()
