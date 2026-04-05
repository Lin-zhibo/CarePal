from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="测试后端 OCR 分析接口")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--username", default="ocr_demo_user")
    p.add_argument("--password", default="demo_pass_123")
    p.add_argument("--images", required=True, help="图片路径，多个用逗号分隔")
    p.add_argument("--prompt", default="请识别药品并分析与帕金森病关系")
    p.add_argument("--output", default="outputs/ocr_result.json")
    p.add_argument("--audio", action="store_true", help="是否让后端把OCR文本转为语音")
    p.add_argument("--audio-output", default="outputs/ocr_result.mp3", help="保存OCR语音文件路径")
    p.add_argument("--timeout", type=int, default=600, help="OCR接口超时时间（秒）")
    p.add_argument("--health-check", action="store_true", help="请求前先进行健康检查")
    return p.parse_args()


def ensure_auth(base_url: str, username: str, password: str) -> str:
    payload = {"username": username, "password": password}
    reg = requests.post(f"{base_url}/auth/register", json=payload, timeout=30)
    if reg.status_code == 200:
        return reg.json()["access_token"]
    if reg.status_code == 409:
        login = requests.post(f"{base_url}/auth/login", json=payload, timeout=30)
        if login.status_code != 200:
            raise RuntimeError(f"登录失败: {login.status_code} {login.text}")
        return login.json()["access_token"]
    raise RuntimeError(f"注册失败: {reg.status_code} {reg.text}")


def main() -> None:
    args = parse_args()
    image_paths = [Path(x.strip()) for x in args.images.split(",") if x.strip()]
    if not image_paths:
        raise RuntimeError("未提供有效图片路径")
    for p in image_paths:
        if not p.exists():
            raise FileNotFoundError(f"图片不存在: {p}")

    token = ensure_auth(args.base_url, args.username, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    if args.health_check:
        h = requests.get(f"{args.base_url}/health", timeout=20)
        print("health:", h.status_code, h.text)

    files = []
    opened = []
    try:
        for p in image_paths:
            f = open(p, "rb")
            opened.append(f)
            files.append(("images", (p.name, f, "application/octet-stream")))

        data = {"prompt": args.prompt, "with_audio": "true" if args.audio else "false"}
        print("开始调用 /ocr/analyze，可能需要较长时间，请耐心等待...")
        resp = requests.post(f"{args.base_url}/ocr/analyze", headers=headers, files=files, data=data, timeout=args.timeout)
    finally:
        for f in opened:
            f.close()

    if resp.status_code != 200:
        raise RuntimeError(f"OCR接口调用失败: {resp.status_code} {resp.text}")

    body = resp.json()
    print(json.dumps(body, ensure_ascii=False, indent=2))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已保存: {out}")

    audio_url = body.get("audio_file_url")
    if args.audio and audio_url:
        audio_resp = requests.get(f"{args.base_url}{audio_url}", headers=headers, timeout=120)
        if audio_resp.status_code != 200:
            raise RuntimeError(f"下载OCR音频失败: {audio_resp.status_code} {audio_resp.text}")
        audio_out = Path(args.audio_output)
        audio_out.parent.mkdir(parents=True, exist_ok=True)
        audio_out.write_bytes(audio_resp.content)
        print(f"OCR语音已保存: {audio_out}")


if __name__ == "__main__":
    main()
