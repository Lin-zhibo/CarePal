# 项目说明（语音 + OCR + 紧急告警后端）

本项目是一个可直接服务化的多模态后端系统，包含以下核心能力：

1. 语音交互链路：ASR -> LLM -> TTS
2. 纯文本对话接口
3. OCR 单Agent图片分析接口
4. 用户注册/登录与鉴权（JWT）
5. 会话记忆与上下文压缩
6. 紧急告警监听与邮件通知

---

## 1. 项目结构

```text
项目根目录/
  doc/
    README.md                 # 当前文档
    API.md                    # 完整接口文档
    requirements.txt          # 依赖
    .env                      # 环境配置（本地）
    docs/
      API_RECOMMENDATIONS.md
      DEPLOYMENT_NOTES.md

  src/
    backend/
      main.py                 # FastAPI入口
      config.py               # 后端配置
      db.py                   # 数据库连接
      models.py               # 用户模型
      security.py             # 密码/JWT
      deps.py                 # 鉴权依赖
      schemas.py              # 请求/响应模型
      services.py             # 业务编排
      prompt_templates.py     # prompt模板（1/2）

    voice_agent/
      pipeline.py             # ASR+LLM+TTS管线
      clients/
        asr_xfyun.py
        llm_xfyun.py
        tts_xfyun.py

    OCR_agent/
      config.py               # OCR配置与客户端创建
      prompts.py              # OCR单Agent提示词
      service.py              # OCR单Agent编排

  demo/
    api_try/
      test_backend_all_api.py     # 全接口联调
      test_backend_voice_api.py   # 语音接口联调
      test_backend_ocr_api.py     # OCR接口联调
      test_emergency_email_alert.py  # 紧急告警邮件测试
```

---

## 2. 快速入门

### 2.1 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r doc/requirements.txt
```

### 2.2 配置环境变量

编辑 `doc/.env`，至少配置：

- 语音链路：
  - `XFYUN_APP_ID`
  - `XFYUN_API_KEY`
  - `XFYUN_API_SECRET`
  - `XFYUN_LLM_API_PASSWORD`
- OCR：
  - `OCR_API_KEY`（推荐直接填）
  - `OCR_AGENT_1_MODEL`
- 紧急告警邮件（可选）：
  - `ALERT_LISTENER_HOST`
  - `ALERT_LISTENER_PORT`
  - `ALERT_EMAIL_SUBJECT`
  - `ALERT_EMAIL_BODY`
  - `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_SENDER_EMAIL`
  - `SMTP_USE_SSL` / `SMTP_USE_TLS`

### 2.3 启动后端

```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

生产并发建议：

```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## 3. 项目流程简述

### 3.1 语音接口流程（`/chat/voice`）

1. 前端上传音频（wav/mp3）
2. 后端做格式识别与保存
3. ASR 识别文本
4. LLM 生成回复（可选prompt模板）
5. 根据 `with_text` / `with_audio` 和业务规则决定：
   - 返回文本
   - 返回音频流或音频下载URL

特别规则：

- `prompt=1` 且识别为 `schedule_edit` 时，不执行TTS，直接返回结构化文本。

### 3.2 OCR接口流程（`/ocr/analyze`）

1. 前端上传一张或多张图片
2. OCR单Agent基于图片和上下文做识别与分析
3. 服务端解析 `<professional_analysis>` 与 `<plain_text>`
4. 后端返回 `plain_text`（已清洗），可选转成音频并返回URL

### 3.3 紧急告警监听流程（TCP）

1. 前端/设备向监听端口发送包含 `token` 的 JSON 报文
2. 后端通过 token 解析用户并查询紧急联系人
3. 后端按模板发送提醒邮件到紧急联系人邮箱
4. 详细协议见 `doc/API.md` 的“紧急告警监听协议”章节

---

## 4. 联调脚本

### 全接口联调

```bash
python demo/api_try/test_backend_all_api.py --base-url http://127.0.0.1:8000 --audio demo/test.wav --prompt 1
```

### OCR接口联调

```bash
python demo/api_try/test_backend_ocr_api.py --images "img/img1.jpg,img/img2.jpg" --health-check --audio
```

### 紧急告警邮件联调

```bash
python demo/api_try/test_emergency_email_alert.py --listener-port 9001 --emergency-contact-name 张三 --emergency-contact-email zhangsan@example.com
```

---

## 5. 接口文档

完整接口定义、参数表、示例请求见：

- `doc/API.md`

## 6. 技术文档

- `doc/TECHNICAL.md`

## 7. 并发测试

并发测试脚本：

- `demo/api_try/test_backend_concurrency.py`

示例：

```bash
python demo/api_try/test_backend_concurrency.py --mode mixed --users 5 --requests-per-user 2 --audio demo/test.wav --images "img/img1.jpg,img/img2.jpg"
```
