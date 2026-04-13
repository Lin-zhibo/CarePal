# 语音助手后端 API 接口文档（标准详版）

项目后端基于 FastAPI，默认本地运行地址：http://127.0.0.1:8000

---

## 一、全局约定

- 遵循 RESTful 风格
- 数据格式：JSON，除音频相关为 multipart/form-data
- 鉴权：Bearer Token（部分接口）
- 状态码及error标准如下文
- 所有示例以 Windows CMD 与 Linux/macOS curl 同时兼容方式展示（特殊处有注释）

---

## 二、接口列表汇总

1. 健康检查 —— GET /health
2. 用户注册 —— POST /auth/register
3. 用户登录 —— POST /auth/login
4. 文本对话 —— POST /chat/text
5. 语音对话 —— POST /chat/voice
6. 语音文件下载 —— GET /chat/voice/file/{filename}

---

## 1. 健康检查

- **方法**：GET
- **路径**：/health
- **鉴权**：无
- **功能说明**：服务就绪性自检接口

### 请求示例（curl）
```sh
curl -X GET http://127.0.0.1:8000/health
```

### 响应参数
| 字段        | 类型    | 说明                 |
| ----------- | ------- | ------------------- |
| status      | string  | 固定 "ok"           |
| app         | string  | 服务名称            |
| version     | string  | 版本号              |

#### 示例：
```json
{
  "status": "ok",
  "app": "voice-agent-backend",
  "version": "1.0.0"
}
```

---

## 2. 用户注册

- **方法**：POST
- **路径**：/auth/register
- **鉴权**：无
- **功能说明**：注册新用户，用户名唯一
- **请求类型**：JSON

### 请求参数
| 字段     | 类型    | 是否必填 | 说明         |
| -------- | ------- | -------- | ------------ |
| username | string  | 是       | 用户名       |
| password | string  | 是       | 密码         |

### curl 调用方式（Windows CMD/LINUX/Mac通用）
```sh
curl -X POST http://127.0.0.1:8000/auth/register -H "Content-Type: application/json" -d "{\"username\":\"test_user\",\"password\":\"1234567\"}"
```

### 响应参数
| 字段         | 类型   | 说明           |
| ------------ | ------ | -------------- |
| access_token | string | JWT Token      |
| token_type   | string | 固定 'bearer'  |
| user         | object | 用户详情       |

#### 示例：
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

---

## 3. 用户登录

- **方法**：POST
- **路径**：/auth/login
- **鉴权**：无
- **功能说明**：用户登录，正确返回access_token
- **请求类型**：JSON

### 请求参数
| 字段     | 类型    | 是否必填 | 说明     |
| -------- | ------- | -------- | -------- |
| username | string  | 是       | 用户名   |
| password | string  | 是       | 密码     |

### curl 调用方式
```sh
curl -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d "{\"username\":\"test_user\",\"password\":\"1234567\"}"
```

### 响应返回
同注册接口响应。

---

## 4. 文本对话接口（LLM）

- **方法**：POST
- **路径**：/chat/text
- **鉴权**：Authorization: Bearer <access_token>
- **请求类型**：JSON

### 请求参数
| 字段     | 类型   | 是否必填 | 说明         |
| -------- | ------ | -------- | ------------ |
| message  | string | 是       | 用户消息文本 |
| prompt   | int(1/2) | 否     | 提示词模板编号 |
| with_text | bool  | 否       | 是否返回文本，默认 true |
| with_audio | bool | 否       | 是否返回TTS音频（URL），默认 false |

> 说明：`prompt` 现在为模板编号，支持 `1` 或 `2`。

### curl 调用方式
```sh
curl -X POST http://127.0.0.1:8000/chat/text -H "Authorization: Bearer <access_token>" -H "Content-Type: application/json" -d "{\"message\":\"你好，请给我一个学习建议\",\"prompt\":\"你是专业学习教练\",\"with_text\":true,\"with_audio\":true}"
```

### 响应参数
| 字段   | 类型   | 说明           |
| ------ | ------ | -------------- |
| answer | string/null | AI回复内容 |
| asr_text | string/null | 文本接口固定为 null |
| assistant_text | string/null | 便于前端统一解析 |
| audio_file_url | string/null | with_audio=true 时返回 |

#### 响应示例：
```json
{
  "answer": "个性化学习建议：......",
  "asr_text": null,
  "assistant_text": "个性化学习建议：......",
  "audio_file_url": "/chat/voice/file/demo_20260330_101010.mp3"
}
```

---
## 5. 语音对话接口（上传音频，返回语音）

- **方法**：POST
- **路径**：/chat/voice
- **鉴权**：Authorization: Bearer <access_token>
- **内容类型**：multipart/form-data

### 请求参数
| 字段    | 类型   | 是否必填 | 说明                     |
| ------- | ------ | -------- | ------------------------ |
| audio   | 文件   | 是       | 支持 WAV(raw)/MP3(lame) |
| prompt | int(1/2) | 否 | 提示词模板编号 |
| with_text | bool/string | 否 | true返回文本，false不返回 |
| with_audio | bool/string | 否 | true返回音频，false不执行TTS |

### curl 调用方式（返回的音频保存为reply.mp3）
```sh
curl -X POST http://127.0.0.1:8000/chat/voice -H "Authorization: Bearer <access_token>" -F "audio=@audio.wav" -F "with_text=false" -F "with_audio=true" --output reply.mp3
```
- 注意：请将 audio.wav 替换为你的实际音频文件名。

#### with_text=true 模式（拿回文本和音频下载URL）
```sh
curl -X POST http://127.0.0.1:8000/chat/voice -H "Authorization: Bearer <access_token>" -F "audio=@audio.wav" -F "prompt=你是资深游戏教练" -F "with_text=true" -F "with_audio=true"
```

### 响应内容
- 默认返回：Content-Type: audio/mpeg，音频流文件
- with_text=true：Content-Type: application/json，附asr文本、助手回答、音频路径
- with_audio=false：返回 JSON，`audio_file_url` 为 null

业务规则补充：

- 当 `prompt=1` 且模型返回 JSON 中 `intent=schedule_edit` 时，后端不会执行 TTS，直接返回 JSON 文本。
- 当 `prompt=1` 且 `intent=normal_chat` 时，仅将 `reply_text` 字段用于 TTS。

#### JSON 响应示例
```json
{
  "asr_text": "今天天气怎么样",
  "assistant_text": "今天天气不错...",
  "audio_file_url": "/chat/voice/file/demo_20260330_101010.mp3"
}
```

---
## 6. 语音文件下载

- **方法**：GET
- **路径**：/chat/voice/file/{filename}
- **鉴权**：Authorization: Bearer <access_token>
- **内容类型**：audio/mpeg

### curl调用方式
```sh
curl -X GET http://127.0.0.1:8000/chat/voice/file/demo_20260330_101010.mp3 -H "Authorization: Bearer <access_token>" --output fetched.mp3
```

---

## 7. 错误码与说明
- 200：成功
- 400：请求参数错误，如空音频文件
- 401：JWT 鉴权失败，未登录/Token失效
- 404：音频文件不存在
- 409：用户名冲突
- 422：参数格式问题
- 500：服务端内部异常

---

## 8. 一键批量接口自动化测试脚本（Python版 test_api.py）

```python
# test_api.py
import requests

def print_resp(r):
    print(f'[status {r.status_code}]', end=' ')
    ct = r.headers.get('content-type','')
    if 'application/json' in ct:
        print(r.json())
    else:
        print('(非JSON返回)', r.content[:80])

api = 'http://127.0.0.1:8000'
username = 'api_demo'  # 可更换
password = 'demo12345'
headers = {'Content-Type': 'application/json'}

print('1. 健康检查:')
r = requests.get(f'{api}/health')
print_resp(r)

print('\n2. 注册:')
r = requests.post(f'{api}/auth/register', headers=headers, json={'username': username, 'password': password})
print_resp(r)
if r.status_code == 409:
    # 用户名冲突时尝试登录
    r = requests.post(f'{api}/auth/login', headers=headers, json={'username': username, 'password': password})

assert r.status_code == 200, '注册或登录失败'
access_token = r.json().get('access_token')

print('\n3. 登录:')
r = requests.post(f'{api}/auth/login', headers=headers, json={'username': username, 'password': password})
print_resp(r)
assert r.status_code == 200

print('\n4. 文本对话:')
headers_auth = {**headers, 'Authorization': f'Bearer {access_token}'}
r = requests.post(f'{api}/chat/text', headers=headers_auth, json={'message': '你好，来一句励志的话'})
print_resp(r)

print('\n5. 语音对话(请准备audio.wav文件):')
try:
    with open('audio.wav', 'rb') as f:
        files = {'audio': f}
        r = requests.post(f'{api}/chat/voice', headers={'Authorization': f'Bearer {access_token}'}, files=files)
    if r.headers.get('content-type','').startswith('audio'):
        with open('reply.mp3', 'wb') as out:
            out.write(r.content)
        print('[语音已保存到 reply.mp3]')
    else:
        print_resp(r)
except FileNotFoundError:
    print('未找到audio.wav，语音接口未测试。')
```

---

## 9. 附录与前端对接注意摘要

- JWT Token 建议保存在前端安全位置（如localStorage），请求时放 Authorization 头。
- Content-Type严格区分：JSON传参用application/json，上传文件用multipart/form-data。
- curl请求在Windows下需注意转义与引号组合（尽量用强制双引号或\），建议多用Postman等工具避免命令行兼容bug
- 前后端分离场景请配置好 CORS，防止跨域问题
- 具体调用见每个接口下 curl 示例

---

## 10. 会话记忆与压缩策略

- 用户隔离方式：基于登录时的 `Bearer token` 进行历史隔离。
- 上下文长度：保留 50 轮（约 100 条 user/assistant 消息）。
- 压缩策略：每满 50 轮触发一次压缩，保留最近10轮原文，较早消息压缩为摘要。

---

如文档需要补充详细响应字段、参数约束规则，请反馈。接口如有调整请同步更新本文件！
