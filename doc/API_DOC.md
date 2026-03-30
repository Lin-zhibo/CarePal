# 语音助手后端接口文档

后端基于 FastAPI，默认本地启动地址：`http://127.0.0.1:8000`

## 1. 健康检查

- 方法：`GET`
- 路径：`/health`
- 说明：检查服务是否可用

响应示例：
```json
{
  "status": "ok",
  "app": "voice-agent-backend",
  "version": "1.0.0"
}
```

## 2. 用户注册

- 方法：`POST`
- 路径：`/auth/register`
- Body（JSON）：
```json
{
  "username": "test_user",
  "password": "12345678"
}
```

成功响应：
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "test_user",
    "created_at": "2026-03-30T10:10:10.000000"
  }
}
```

## 3. 用户登录

- 方法：`POST`
- 路径：`/auth/login`
- Body（JSON）：
```json
{
  "username": "test_user",
  "password": "12345678"
}
```

成功响应同注册。

---

## 4. 文本对话（LLM）

- 方法：`POST`
- 路径：`/chat/text`
- 鉴权：`Authorization: Bearer <access_token>`
- Body（JSON）：
```json
{
  "message": "你好，请给我一个学习建议"
}
```

响应：
```json
{
  "answer": "...模型回复内容..."
}
```

### 调用示例

#### curl
```sh
curl -X POST http://127.0.0.1:8000/chat/text \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "你好，请给我一个学习建议"}'
```

#### Python
```python
import requests
url = "http://127.0.0.1:8000/chat/text"
token = "<access_token>"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
body = {"message": "你好，请给我一个学习建议"}
resp = requests.post(url, json=body, headers=headers)
print(resp.status_code, resp.json())
```

---

## 5. 语音对话（上传音频，返回语音）

- 方法：`POST`
- 路径：`/chat/voice`
- 鉴权：`Authorization: Bearer <access_token>`
- Content-Type：`multipart/form-data`
- 字段：
  - `audio`: 音频文件（支持 `.wav(raw)` 和 `.mp3(lame)`）
  - `with_text`: 可选布尔参数（`true/false`）

响应：
- 默认：直接返回 `audio/mpeg` 文件流（后端合成后的语音）
- 当 `with_text=true`：返回 JSON，包含 ASR 文本、LLM 回复文本、音频下载 URL

`with_text=true` 响应示例：

```json
{
  "asr_text": "今天天气怎么样",
  "assistant_text": "今天天气不错...",
  "audio_file_url": "/chat/voice/file/demo_20260330_101010.mp3"
}
```

### 调用示例

#### curl
```sh
curl -X POST http://127.0.0.1:8000/chat/voice \
  -H "Authorization: Bearer <access_token>" \
  -F "audio=@audio.wav" \
  -F "with_text=false" \
  --output reply.mp3
```
- 注意：`audio.wav` 替换为你实际的音频文件；`reply.mp3` 为保存的返回语音文件

#### Python
```python
import requests
import os
from playsound import playsound
url = "http://127.0.0.1:8000/chat/voice"
token = "<access_token>"
headers = {"Authorization": f"Bearer {token}"}
with open("audio.wav", "rb") as f:
    files = {"audio": f}
    data = {"with_text": "false"}
    resp = requests.post(url, headers=headers, files=files, data=data)
if resp.headers.get("content-type", "").startswith("audio"):
    with open("reply.mp3", "wb") as fp:
        fp.write(resp.content)
    playsound("reply.mp3")
else:
    print("Error:", resp.status_code, resp.text)
```
- 注意：需提前安装 requests 和 playsound 库，可用 `pip install requests playsound`
- `audio.wav` 替换为你实际的音频文件；成功将自动播放返回音频

### with_text=true 模式（先拿文本+文件URL）

```python
import requests
url = "http://127.0.0.1:8000/chat/voice"
token = "<access_token>"
headers = {"Authorization": f"Bearer {token}"}

with open("audio.mp3", "rb") as f:
    resp = requests.post(
        url,
        headers=headers,
        files={"audio": f},
        data={"with_text": "true"}
    )

print(resp.json())
```

### 下载语音文件接口

- 方法：`GET`
- 路径：`/chat/voice/file/{filename}`
- 鉴权：`Authorization: Bearer <access_token>`

---

## 6. 认证说明

受保护接口（`/chat/text`, `/chat/voice`）必须带 JWT：
```text
Authorization: Bearer <access_token>
```

## 7. 常见状态码
- `200`: 成功
- `400`: 请求参数错误（如空音频文件）
- `401`: 未登录或 token 无效
- `404`: 音频文件不存在
- `409`: 注册用户名冲突
- `500`: 服务端异常（例如第三方 API 调用失败）
