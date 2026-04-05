from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="测试后端语音交互API并保存返回音频")
    p.add_argument("--base-url", default="http://127.0.0.1:8000", help="后端地址")
    p.add_argument("--username", default="demo_user", help="测试用户名")
    p.add_argument("--password", default="demo_pass_123", help="测试密码")
    p.add_argument("--audio", required=True, help="待上传音频路径（wav/mp3）")
    p.add_argument("--output", default="outputs/backend_api_reply.mp3", help="保存后端返回音频路径")
    p.add_argument("--with-text", action="store_true", help="使用with_text模式：先拿文本和文件URL，再二次下载音频")
    p.add_argument("--with-audio", action="store_true", help="是否让后端执行TTS并返回音频")
    p.add_argument("--prompt", default="", help="自定义提示词")
    return p


def ensure_token(base_url: str, username: str, password: str) -> str:
    reg_url = f"{base_url}/auth/register"
    login_url = f"{base_url}/auth/login"
    payload = {"username": username, "password": password}

    reg_resp = requests.post(reg_url, json=payload, timeout=30)
    if reg_resp.status_code in (200, 201):
        return reg_resp.json()["access_token"]
    if reg_resp.status_code != 409:
        raise RuntimeError(f"注册失败: {reg_resp.status_code} {reg_resp.text}")

    login_resp = requests.post(login_url, json=payload, timeout=30)
    if login_resp.status_code != 200:
        raise RuntimeError(f"登录失败: {login_resp.status_code} {login_resp.text}")
    return login_resp.json()["access_token"]


def main() -> None:
    args = build_parser().parse_args()
    audio_path = Path(args.audio)
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    token = ensure_token(args.base_url, args.username, args.password)
    headers = {"Authorization": f"Bearer {token}"}
    voice_url = f"{args.base_url}/chat/voice"

    with open(audio_path, "rb") as f:
        files = {"audio": (audio_path.name, f, "application/octet-stream")}
        data = {
            "with_text": "true" if args.with_text else "false",
            "with_audio": "true" if args.with_audio else "false",
        }
        if args.prompt:
            data["prompt"] = args.prompt
        resp = requests.post(voice_url, headers=headers, files=files, data=data, timeout=600)

    if resp.status_code != 200:
        raise RuntimeError(f"语音接口调用失败: {resp.status_code} {resp.text}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if args.with_text:
        payload = resp.json()
        print("[with_text响应]\n" + json.dumps(payload, ensure_ascii=False, indent=2))
        audio_file_url = payload.get("audio_file_url")
        if audio_file_url:
            file_url = f"{args.base_url}{audio_file_url}"
            file_resp = requests.get(file_url, headers=headers, timeout=120)
            if file_resp.status_code != 200:
                raise RuntimeError(f"下载语音文件失败: {file_resp.status_code} {file_resp.text}")
            output_path.write_bytes(file_resp.content)
            print(f"保存完成: {output_path}")
        else:
            print("本次 with_audio=false，未返回音频文件。")
    else:
        output_path.write_bytes(resp.content)
        print(f"保存完成: {output_path}")


if __name__ == "__main__":
    main()
