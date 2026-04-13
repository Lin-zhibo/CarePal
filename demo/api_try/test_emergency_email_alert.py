from __future__ import annotations

import argparse
import json
import socket

import requests


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="触发后端紧急联系人告警邮件测试")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--username", default="alert_demo_user")
    p.add_argument("--password", default="demo_pass_123")
    p.add_argument("--emergency-contact-name", required=True)
    p.add_argument("--emergency-contact-email", required=True)
    p.add_argument("--listener-host", default="127.0.0.1")
    p.add_argument("--listener-port", type=int, required=True)
    p.add_argument("--qq-email", default="", help="发送邮箱，例如 123456@qq.com（可选，传入则覆盖后端env）")
    p.add_argument("--qq-password", default="", help="QQ邮箱 SMTP 授权码（可选，传入则覆盖后端env）")
    p.add_argument("--smtp-host", default="smtp.qq.com")
    p.add_argument("--smtp-port", type=int, default=465)
    p.add_argument("--smtp-ssl", action="store_true", help="是否使用 SMTP_SSL，QQ推荐开启")
    p.add_argument("--smtp-tls", action="store_true", help="是否使用 STARTTLS")
    p.add_argument("--use-smtp-override", action="store_true", help="是否在触发报文中覆盖后端 SMTP 配置")
    p.add_argument("--timeout", type=int, default=30)
    return p.parse_args()


def ensure_auth(
    base_url: str,
    username: str,
    password: str,
    emergency_contact_name: str,
    emergency_contact_email: str,
    timeout: int,
) -> str:
    register_payload = {
        "username": username,
        "password": password,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_email": emergency_contact_email,
    }
    login_payload = {"username": username, "password": password}

    reg = requests.post(f"{base_url}/auth/register", json=register_payload, timeout=timeout)
    if reg.status_code == 200:
        return reg.json()["access_token"]
    if reg.status_code == 409:
        login = requests.post(f"{base_url}/auth/login", json=login_payload, timeout=timeout)
        if login.status_code != 200:
            raise RuntimeError(f"登录失败: {login.status_code} {login.text}")
        return login.json()["access_token"]
    raise RuntimeError(f"注册失败: {reg.status_code} {reg.text}")


def main() -> None:
    args = parse_args()

    token = ensure_auth(
        args.base_url,
        args.username,
        args.password,
        args.emergency_contact_name,
        args.emergency_contact_email,
        args.timeout,
    )

    payload = {
        "type": "emergency_fall_alert",
        "version": "1.0",
        "token": token,
    }

    should_override = args.use_smtp_override or bool(args.qq_email.strip()) or bool(args.qq_password.strip())
    if should_override:
        payload["smtp_override"] = {
            "smtp_host": args.smtp_host,
            "smtp_port": args.smtp_port,
            "smtp_username": args.qq_email,
            "smtp_password": args.qq_password,
            "smtp_sender_email": args.qq_email,
            "smtp_use_ssl": args.smtp_ssl,
            "smtp_use_tls": args.smtp_tls,
        }

    message = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    with socket.create_connection((args.listener_host, args.listener_port), timeout=args.timeout) as sock:
        sock.sendall(message)

    print("触发请求已发送，请查看后端日志确认邮件发送结果。")
    print(f"用户: {args.username}")
    print(f"紧急联系人: {args.emergency_contact_name} <{args.emergency_contact_email}>")


if __name__ == "__main__":
    main()
