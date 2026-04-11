# 项目说明（语音 + OCR 多Agent 后端）

本项目是一个可直接服务化的多模态后端系统，包含以下核心能力：

1. 语音交互链路：ASR -> LLM -> TTS
2. 纯文本对话接口
3. OCR 多Agent图片分析接口
4. 用户注册/登录与鉴权（JWT）
5. 会话记忆与上下文压缩

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
      prompts.py              # OCR三Agent提示词
      service.py              # OCR多Agent编排

  demo/
    api_try/
      test_backend_all_api.py     # 全接口联调
      test_backend_voice_api.py   # 语音接口联调
      test_backend_ocr_api.py     # OCR接口联调
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
  - `LLM_MODEL`（Agent2/3 使用，默认 4.0Ultra）

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
2. Agent1（视觉OCR模型）提取图片关键信息
3. Agent2（LLM_MODEL）进行专业分析
4. Agent3（LLM_MODEL）做通俗化改写
5. 后端仅返回 Agent3 文本（已清洗），可选转成音频并返回URL

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
