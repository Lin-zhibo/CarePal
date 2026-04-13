# 后端 API 使用说明（完整）

本文档覆盖当前项目全部后端接口，包含参数定义、返回结构、调用示例及前后端对接要点。

基础地址：`http://127.0.0.1:8000`

## 1. 认证与全局约定

- 除 `/health`、`/auth/register`、`/auth/login` 外，其余接口都需要 JWT。
- 认证头：`Authorization: Bearer <access_token>`
- 通用状态码：
  - `200` 成功
  - `400` 请求参数错误
  - `401` 未认证或 token 失效
  - `404` 文件不存在
  - `409` 用户名冲突
  - `422` 参数校验失败
  - `500` 服务内部错误

---

## 2. 健康检查

### GET `/health`

用途：检测后端是否正常运行。

响应：

```json
{
  "status": "ok",
  "app": "voice-agent-backend",
  "version": "1.0.0"
}
```

---

## 3. 用户注册与登录

### POST `/auth/register`

请求 JSON：

| 字段     | 类型   | 必填 | 说明           |
| -------- | ------ | ---- | -------------- |
| username | string | 是   | 用户名（3-64） |
| password | string | 是   | 密码（6-128）  |

### POST `/auth/login`

请求 JSON 同上。

注册/登录响应：

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "demo",
    "created_at": "2026-01-01T00:00:00"
  }
}
```

---

## 4. 文本对话

### POST `/chat/text`

请求 JSON：

| 字段       | 类型   | 必填 | 默认  | 说明                                |
| ---------- | ------ | ---- | ----- | ----------------------------------- |
| message    | string | 是   | -     | 用户输入文本                        |
| prompt     | int    | 否   | null  | 提示词模板编号，支持 `1` 或 `2` |
| with_text  | bool   | 否   | true  | 是否返回文本字段                    |
| with_audio | bool   | 否   | false | 是否执行TTS并返回音频URL            |

响应 JSON：

| 字段              | 类型        | 说明                                      |
| ----------------- | ----------- | ----------------------------------------- |
| answer            | string/null | 便捷文本返回                              |
| asr_text          | string/null | 文本接口固定 null                         |
| assistant_text    | string/null | 助手文本结果                              |
| assistant_payload | object/null | 若模型返回可解析结构化 JSON，则返回该对象 |
| audio_file_url    | string/null | with_audio=true 且成功生成音频时返回      |

业务规则：

- `prompt=1` 且识别到 `intent=normal_chat`：仅 `reply_text` 会被用于文本输出和 TTS。
- `prompt=1` 且识别到 `intent=schedule_edit`：不执行 TTS，直接返回结构化文本。

---

## 5. 语音对话

### POST `/chat/voice`

请求类型：`multipart/form-data`

| 字段       | 类型        | 必填 | 默认  | 说明                                          |
| ---------- | ----------- | ---- | ----- | --------------------------------------------- |
| audio      | file        | 是   | -     | 输入音频，支持 `.wav(raw)` / `.mp3(lame)` |
| prompt     | int         | 否   | null  | 提示词模板编号，支持 `1` 或 `2`           |
| with_text  | bool/string | 否   | false | 是否返回 ASR + LLM 文本                       |
| with_audio | bool/string | 否   | true  | 是否执行TTS并返回音频                         |

响应规则：

1. `with_audio=true` 且本轮允许TTS：

   - 若 `with_text=false`：直接返回 `audio/mpeg` 文件流
   - 若 `with_text=true`：返回 JSON（包含 `audio_file_url`）
2. `with_audio=false` 或业务规则禁止TTS（如 `prompt=1` + `schedule_edit`）：

   - 返回 JSON，不返回音频流

JSON 响应字段：

| 字段              | 类型        | 说明                                         |
| ----------------- | ----------- | -------------------------------------------- |
| asr_text          | string/null | ASR识别文本（with_text=false 时通常为 null） |
| assistant_text    | string/null | LLM文本结果                                  |
| assistant_payload | object/null | 结构化结果（若可解析）                       |
| audio_file_url    | string/null | 生成音频时可下载地址                         |

---

## 6. 语音文件下载

### GET `/chat/voice/file/{filename}`

用途：下载语音接口或 OCR 生成的音频文件。

响应类型：`audio/mpeg`

---

## 7. OCR 图片分析（多Agent）

### POST `/ocr/analyze`

请求类型：`multipart/form-data`

| 字段       | 类型        | 必填 | 默认       | 说明                           |
| ---------- | ----------- | ---- | ---------- | ------------------------------ |
| images     | file[]      | 是   | -          | 一张或多张图片（png/jpg/jpeg） |
| prompt     | string      | 否   | 默认提示词 | 用户补充问题                   |
| with_audio | bool/string | 否   | false      | 是否把最终 OCR 文本转语音      |

响应 JSON：

| 字段           | 类型        | 说明                                               |
| -------------- | ----------- | -------------------------------------------------- |
| text           | string      | 返回给前端的最终文本（仅Agent3结果，已做格式清洗） |
| audio_file_url | string/null | with_audio=true 且TTS成功时返回                    |

说明：

- Agent1：使用 OCR 视觉模型（`OCR_AGENT_1_MODEL`）
- Agent2/3：使用通用 LLM（`LLM_MODEL=4.0Ultra`）
- OCR 返回给前端仅保留清洗后的 Agent3 文本，便于前端展示与 TTS。

## 8. 快速调用示例

### 8.1 文本对话

```bash
curl -X POST http://127.0.0.1:8000/chat/text \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"你好","prompt":1,"with_text":true,"with_audio":false}'
```

### 8.2 语音对话（返回音频流）

```bash
curl -X POST http://127.0.0.1:8000/chat/voice \
  -H "Authorization: Bearer <access_token>" \
  -F "audio=@demo.wav" \
  -F "prompt=1" \
  -F "with_text=false" \
  -F "with_audio=true" \
  --output reply.mp3
```

### 8.3 OCR 图片分析

```bash
curl -X POST http://127.0.0.1:8000/ocr/analyze \
  -H "Authorization: Bearer <access_token>" \
  -F "images=@img1.jpg" \
  -F "images=@img2.jpg" \
  -F "prompt=请分析与帕金森病关系" \
  -F "with_audio=true"
```
