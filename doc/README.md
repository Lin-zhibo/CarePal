# ASR + LLM + TTS 语音助手（优先使用 API）

本项目是一个完整的语音交互系统工程模板，集成了：

1. ASR（语音转文本）——调用外部 API
2. LLM（大模型推理/对话）——调用外部 API
3. TTS（文本转语音）——调用外部 API

核心包含：

- 可直接运行的 Python 代码
- 模块化模型服务适配（各自独立插件）
- 对话记忆（上下文保存）
- 命令行交互
- API 选型建议文档
- 本地部署与设备性能要求说明

## 1）推荐免费/低价API测试接口

详细可见 `docs/API_RECOMMENDATIONS.md`。

本工程默认实现（已统一为科大讯飞）：

- ASR：讯飞语音听写（IAT）API
- LLM：讯飞星火大模型 API
- TTS：讯飞在线语音合成 API

## 2）项目结构

```
项目根目录/
  doc/
    README.md
    requirements.txt
    .env.example
    docs/
      API_RECOMMENDATIONS.md
      DEPLOYMENT_NOTES.md
  src/
    voice_agent/
      __init__.py
      config.py
      utils.py
      pipeline.py
      cli.py
      clients/
        __init__.py
        asr_xfyun.py
        llm_xfyun.py
        tts_xfyun.py
```

## 3）快速开始

**A. 安装依赖：**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r doc/requirements.txt
```

**B. 配置环境变量：**
```bash
copy doc/.env.example .env
```
编辑`.env`文件，填写必需的讯飞密钥：
- `XFYUN_APP_ID`
- `XFYUN_API_KEY`
- `XFYUN_API_SECRET`
- `XFYUN_LLM_API_PASSWORD`（星火 HTTP 接口 Bearer 密钥）

**C. 单轮音频流水：**
```bash
python -m src.voice_agent.cli --audio sample.wav --output outputs/reply.mp3
```
输出结果：
- 识别出的文字
- 大模型回复
- 合成的语音文件

**D. 交互模式：**
```bash
python -m src.voice_agent.cli
```
命令行内支持：
- `t` 文本对话轮
- `a` 输入音频路径进行语音轮
- `q` 退出

默认对话记忆保存在 `memory/history.json`。

**E. 终端语音助手模式（自动麦克风检测 + 自动播报）：**
```bash
python -m src.voice_agent.cli --live
```
说明：`--live` 现在是“用户主动触发”模式，不会持续后台监听；输入 `r` 才开始录音一轮，输入 `q` 退出。
可选参数：
- `--no-autoplay`：不自动播放 TTS
- `--mic-threshold 0.015`：麦克风触发阈值
- `--silence-seconds 1.0`：静音判停时长
- `--max-record-seconds 20`：单句最长录音时长

示例：
```bash
python -m src.voice_agent.cli --live --mic-threshold 0.012 --silence-seconds 0.8
```

## 4）说明

- 音频输入建议为清晰的 16k 单声道 PCM WAV，以提升讯飞ASR稳定性。
- ASR 支持 `.wav`（raw）与 `.mp3`（lame）；MP3 若含 ID3 信息会自动清理头尾标签。
- API额度/免费量耗尽时，会收到错误码（如鉴权失败、流控超限）。
- TTS不生效时，可更换`.env`中的 `TTS_VOICE`（如 `x4_mingge` 等已开通发音人）。
- 本工程当前对接的是 demo 同款接口：ASR 使用流式 WebSocket，LLM 使用 `spark-api-open` HTTP 流式，TTS 使用任务创建/查询接口。

## 5）可扩展建议

- 增加端点检测（VAD）和麦克风实时流处理
- 补充Web UI（FastAPI + 前端页面）
- 增加多API备用/fallback能力（如讯飞优先、文心或通义兜底）

## 6）后端服务化（FastAPI）

已提供后端工程入口：`src/backend/main.py`

启动命令：

```bash
uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

默认能力：

- `GET /health`：健康检查
- `POST /auth/register`：注册
- `POST /auth/login`：登录
- `POST /chat/text`：纯文本对话
- `POST /chat/voice`：上传音频并返回合成语音（支持 wav/mp3）
- `GET /chat/voice/file/{filename}`：下载语音文件（with_text模式）

接口细节见：`doc/API_DOC.md`

后端语音接口联调脚本：`demo/api_try/test_backend_voice_api.py`
