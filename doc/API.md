# 后端接口文档（前端对接）

基础地址：`http://127.0.0.1:8000`

认证规则：
- 除 `/health`、`/auth/register`、`/auth/login`、`/auth/login_weixin` 外，其余接口都需要 JWT。
- Header：`Authorization: Bearer <access_token>`

通用状态码：
- `200` 成功
- `400` 参数或业务错误
- `401` 未认证或 token 失效
- `404` 文件不存在
- `409` 账号已存在
- `422` 请求体校验失败
- `500` 服务内部异常

---

## 1) 健康检查

### GET `/health`

响应 JSON：

```json
{
  "status": "ok",
  "app": "voice-agent-backend",
  "version": "1.0.0"
}
```

---

## 2) 账号注册

### POST `/auth/register`

请求 JSON：

```json
{
  "username": "alice",
  "password": "12345678",
  "emergency_contact_name": "Bob",
  "emergency_contact_email": "bob@example.com"
}
```

响应 JSON：

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "alice",
    "created_at": "2026-01-01T00:00:00"
  }
}
```

---

## 3) 账号密码登录

### POST `/auth/login`

请求 JSON：

```json
{
  "username": "alice",
  "password": "12345678"
}
```

响应 JSON（同注册）：

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "alice",
    "created_at": "2026-01-01T00:00:00"
  }
}
```

---

## 4) 微信小程序登录

### POST `/auth/login_weixin`

说明：
- 前端传小程序 `code`
- 后端向微信 `jscode2session` 换取 `openid/session_key`
- 使用 `openid` 作为用户名、`session_key` 作为口令参与本系统登录流程
- 流程：先登录，失败则注册后再登录
- 微信登录不要求紧急联系人信息

请求 JSON：

```json
{
  "code": "wx-login-code-from-mini-program"
}
```

响应 JSON（同注册/登录）：

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 12,
    "username": "o2hXg5...openid...",
    "created_at": "2026-01-01T00:00:00"
  }
}
```

---

## 5) 获取当前用户紧急联系人

### GET `/auth/emergency-contact`

请求头：`Authorization: Bearer <token>`

响应 JSON：

```json
{
  "emergency_contact_name": "Bob",
  "emergency_contact_email": "bob@example.com"
}
```

---

## 6) 文本对话

### POST `/chat/text`

请求 JSON：

```json
{
  "message": "今天药该怎么吃？",
  "prompt": 1,
  "with_text": true,
  "with_audio": false
}
```

字段说明：
- `prompt`: 可空，当前支持 `1` 或 `2`
- `with_text`: 是否返回文本字段
- `with_audio`: 是否做 TTS 并返回音频 URL

响应 JSON：

```json
{
  "answer": "...",
  "asr_text": null,
  "assistant_text": "...",
  "assistant_payload": null,
  "audio_file_url": null
}
```

---

## 7) 语音对话

### POST `/chat/voice`

请求类型：`multipart/form-data`

表单字段：
- `audio`: 音频文件（必填，支持 wav/mp3）
- `prompt`: 可选，`1` 或 `2`
- `with_text`: 可选，默认 `false`
- `with_audio`: 可选，默认 `true`

示例（curl）：

```bash
curl -X POST http://127.0.0.1:8000/chat/voice \
  -H "Authorization: Bearer <token>" \
  -F "audio=@demo.wav" \
  -F "prompt=1" \
  -F "with_text=true" \
  -F "with_audio=true"
```

响应：
- 若 `with_audio=true` 且 `with_text=false`，可能直接返回音频流 `audio/mpeg`
- 其余情况返回 JSON：

```json
{
  "asr_text": "...",
  "assistant_text": "...",
  "assistant_payload": null,
  "audio_file_url": "/chat/voice/file/xxx.mp3"
}
```

---

## 8) 语音文件下载

### GET `/chat/voice/file/{filename}`

用途：下载语音回复文件

响应类型：`audio/mpeg`

---

## 9) OCR 图片分析

### POST `/ocr/analyze`

请求类型：`multipart/form-data`

表单字段：
- `images`: 图片文件数组（必填，支持 png/jpg/jpeg）
- `prompt`: 可选文字补充
- `with_audio`: 可选，默认 `false`
- `with_medication_extraction`: 可选，默认 `true`，是否提取用药 JSON 并尝试动态写入 RAG

示例（curl）：

```bash
curl -X POST http://127.0.0.1:8000/ocr/analyze \
  -H "Authorization: Bearer <token>" \
  -F "images=@img1.jpg" \
  -F "prompt=请分析" \
  -F "with_audio=false" \
  -F "with_medication_extraction=true"
```

响应 JSON：

```json
{
  "text": "...专业分析文本...",
  "audio_file_url": null,
  "medication_json": {
    "medicines": [
      {
        "药品名": "",
        "单次剂量": "",
        "每日频次": "",
        "服药时间": "",
        "注意事项": ""
      }
    ]
  },
  "rag_ingested_count": 1
}
```

说明：
- `text` 现在返回 OCR 的专业输出
- `rag_ingested_count` 表示本次动态写入 RAG 的新增条数

---

## 10) 紧急告警监听（非 HTTP）

说明：该能力不是 REST API。后端在 `ALERT_LISTENER_HOST:ALERT_LISTENER_PORT` 监听 TCP JSON 报文。

最小报文：

```json
{
  "token": "<jwt-token>"
}
```

可选字段：
- `type`: 若传，必须是 `emergency_fall_alert`
- `version`: 协议版本

邮件发送规则：
- 后端根据 token 找到用户及紧急联系人
- 按模板发送邮件到联系人邮箱
