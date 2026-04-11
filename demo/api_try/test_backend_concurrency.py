from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="后端并发测试脚本（text/voice/ocr/mixed）")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--mode", choices=["text", "voice", "ocr", "mixed"], default="text")
    p.add_argument("--users", type=int, default=5, help="并发用户数")
    p.add_argument("--requests-per-user", type=int, default=3, help="每个用户发起请求数")
    p.add_argument("--prompt", type=int, default=1, choices=[1, 2])
    p.add_argument("--same-token", action="store_true", help="所有并发请求共享同一token（用于验证会话锁串行）")
    p.add_argument("--audio", default="", help="voice/mixed模式必填，wav或mp3")
    p.add_argument("--images", default="", help="ocr/mixed模式必填，逗号分隔图片路径")
    p.add_argument("--timeout", type=int, default=300)
    return p.parse_args()


def ensure_auth(base_url: str, username: str, password: str, timeout: int) -> str:
    payload = {"username": username, "password": password}
    reg = requests.post(f"{base_url}/auth/register", json=payload, timeout=timeout)
    if reg.status_code == 200:
        return reg.json()["access_token"]
    if reg.status_code == 409:
        login = requests.post(f"{base_url}/auth/login", json=payload, timeout=timeout)
        if login.status_code != 200:
            raise RuntimeError(f"登录失败: {login.status_code} {login.text}")
        return login.json()["access_token"]
    raise RuntimeError(f"注册失败: {reg.status_code} {reg.text}")


def call_text(base_url: str, token: str, prompt: int, timeout: int, idx: int) -> tuple[bool, float, str]:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "message": f"并发测试消息 #{idx}，请简短回复。",
        "prompt": prompt,
        "with_text": True,
        "with_audio": False,
    }
    t0 = time.perf_counter()
    resp = requests.post(f"{base_url}/chat/text", headers=headers, json=body, timeout=timeout)
    cost = time.perf_counter() - t0
    if resp.status_code != 200:
        return False, cost, f"{resp.status_code} {resp.text}"
    return True, cost, "ok"


def call_voice(base_url: str, token: str, prompt: int, timeout: int, audio_path: Path) -> tuple[bool, float, str]:
    headers = {"Authorization": f"Bearer {token}"}
    with audio_path.open("rb") as f:
        files = {"audio": (audio_path.name, f, "application/octet-stream")}
        data = {"prompt": str(prompt), "with_text": "true", "with_audio": "false"}
        t0 = time.perf_counter()
        resp = requests.post(f"{base_url}/chat/voice", headers=headers, files=files, data=data, timeout=timeout)
        cost = time.perf_counter() - t0
    if resp.status_code != 200:
        return False, cost, f"{resp.status_code} {resp.text}"
    return True, cost, "ok"


def call_ocr(base_url: str, token: str, timeout: int, images: list[Path]) -> tuple[bool, float, str]:
    headers = {"Authorization": f"Bearer {token}"}
    opened = []
    files = []
    try:
        for p in images:
            f = open(p, "rb")
            opened.append(f)
            files.append(("images", (p.name, f, "application/octet-stream")))
        data = {"prompt": "并发测试：请输出药品分析摘要", "with_audio": "false"}
        t0 = time.perf_counter()
        resp = requests.post(f"{base_url}/ocr/analyze", headers=headers, files=files, data=data, timeout=timeout)
        cost = time.perf_counter() - t0
    finally:
        for f in opened:
            f.close()
    if resp.status_code != 200:
        return False, cost, f"{resp.status_code} {resp.text}"
    return True, cost, "ok"


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    idx = max(0, min(len(arr) - 1, int((len(arr) - 1) * ratio)))
    return arr[idx]


def main() -> None:
    args = parse_args()
    total_tasks = args.users * args.requests_per_user

    audio_path = Path(args.audio) if args.audio else None
    if args.mode in {"voice", "mixed"}:
        if not audio_path or not audio_path.exists():
            raise RuntimeError("voice/mixed 模式需要有效 --audio")

    images: list[Path] = []
    if args.mode in {"ocr", "mixed"}:
        raw = [x.strip() for x in args.images.split(",") if x.strip()]
        images = [Path(x) for x in raw]
        if not images or any(not p.exists() for p in images):
            raise RuntimeError("ocr/mixed 模式需要有效 --images")

    print("准备认证...")
    tokens: list[str] = []
    if args.same_token:
        token = ensure_auth(args.base_url, "cc_shared_user", "demo_pass_123", args.timeout)
        tokens = [token for _ in range(args.users)]
    else:
        for i in range(args.users):
            tokens.append(ensure_auth(args.base_url, f"cc_user_{i}", "demo_pass_123", args.timeout))

    def submit_one(user_idx: int, req_idx: int) -> tuple[bool, float, str]:
        token = tokens[user_idx]
        if args.mode == "text":
            return call_text(args.base_url, token, args.prompt, args.timeout, req_idx)
        if args.mode == "voice":
            return call_voice(args.base_url, token, args.prompt, args.timeout, audio_path)  # type: ignore[arg-type]
        if args.mode == "ocr":
            return call_ocr(args.base_url, token, args.timeout, images)
        # mixed: 按序轮换
        mod = req_idx % 3
        if mod == 0:
            return call_text(args.base_url, token, args.prompt, args.timeout, req_idx)
        if mod == 1:
            return call_voice(args.base_url, token, args.prompt, args.timeout, audio_path)  # type: ignore[arg-type]
        return call_ocr(args.base_url, token, args.timeout, images)

    print(
        f"开始并发测试: mode={args.mode}, users={args.users}, req/user={args.requests_per_user}, total={total_tasks}, same_token={args.same_token}"
    )
    t_start = time.perf_counter()
    results = []
    with ThreadPoolExecutor(max_workers=args.users) as ex:
        futures = []
        for u in range(args.users):
            for r in range(args.requests_per_user):
                futures.append(ex.submit(submit_one, u, r + 1))

        for fut in as_completed(futures):
            results.append(fut.result())

    total_cost = time.perf_counter() - t_start
    ok_costs = [x[1] for x in results if x[0]]
    fail_items = [x for x in results if not x[0]]

    report = {
        "mode": args.mode,
        "users": args.users,
        "requests_per_user": args.requests_per_user,
        "total_requests": total_tasks,
        "success": len(ok_costs),
        "failed": len(fail_items),
        "total_time_sec": round(total_cost, 3),
        "throughput_rps": round(total_tasks / total_cost, 3) if total_cost > 0 else 0,
        "latency": {
            "avg_sec": round(sum(ok_costs) / len(ok_costs), 3) if ok_costs else 0,
            "p50_sec": round(percentile(ok_costs, 0.5), 3) if ok_costs else 0,
            "p95_sec": round(percentile(ok_costs, 0.95), 3) if ok_costs else 0,
            "max_sec": round(max(ok_costs), 3) if ok_costs else 0,
        },
        "sample_failures": [x[2] for x in fail_items[:5]],
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
