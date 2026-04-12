# 系统架构文档

本文档描述 CarePal 后端系统的整体架构设计、模块边界与关键设计决策。

---

## 目录组织结构

### 一、项目根目录

```
CarePal/                          # 项目根目录
├── doc/                          # 项目文档（部署说明、接口协议、技术细节）
├── src/                          # 核心源代码
├── demo/                         # 联调测试脚本
├── util/                         # 独立工具（C++ 跌倒检测、辅助脚本）
├── models/                       # 模型权重文件
├── data/                         # 静态数据（问答对、知识库等）
├── dataset/                      # 原始数据集（视频、图片）
├── db/                           # 数据库文件（SQLite 等）
├── log/                          # 运行日志输出
└── .env                          # 根目录环境变量（可选，doc/.env 优先）
```

### 二、doc/ — 项目文档

```
doc/
├── README.md                     # 项目说明、快速入门、联调指南
├── API.md                        # 完整接口文档（参数、响应、示例）
├── ARCHITECTURE.md               # 本文件，架构设计文档
├── TECHNICAL.md                  # 技术细节（并发、配置、压测）
├── requirements.txt              # Python 依赖清单
└── .env                          # 环境变量配置（讯飞密钥、数据库、JWT 等）
```

> **说明：** 所有密钥和敏感配置集中在 `doc/.env`，不提交到版本控制。`src/` 各模块通过 `dotenv` 加载此文件。

### 三、src/ — 源代码

```
src/
├── __init__.py
├── backend/                      # FastAPI 后端（HTTP 入口 + 业务编排）
├── voice_agent/                  # 语音 Agent（ASR + LLM + TTS 管线）
├── OCR_agent/                    # OCR 多 Agent（视觉 + 专业分析 + 通俗化）
└── RAG/                          # 检索增强生成模块（知识库向量检索）
```

#### 3.1 src/backend/ — FastAPI 后端

```
backend/
├── __init__.py
├── main.py                       # FastAPI 入口：路由定义、请求入口、响应封装
├── config.py                     # 后端配置（APP_NAME、JWT、DATABASE_URL）
├── db.py                         # SQLAlchemy 连接与会话管理
├── models.py                     # 数据库 ORM 模型（如 User）
├── schemas.py                    # Pydantic 请求/响应模型
├── deps.py                       # 依赖注入（get_current_user、AuthContext）
├── security.py                   # 密码哈希与 JWT token 创建/验证
├── services.py                   # 业务编排层（会话管理、响应加工）
└── prompt_templates.py            # Prompt 模板字典（prompt_id=1 康复助手、prompt_id=2 周报助手）
```

#### 3.2 src/voice_agent/ — 语音 Agent

```
voice_agent/
├── __init__.py
├── config.py                     # 语音链路配置（讯飞密钥、模型名称、TTS 参数、RAG 配置）
├── pipeline.py                   # 核心管线：ASR → LLM → TTS 的编排逻辑
├── rag.py                        # 轻量 RAG 实现：知识库向量检索与上下文拼接
├── utils.py                      # 通用工具（历史读写、上下文截断）
├── cli.py                        # 命令行入口（独立运行语音对话）
├── live_terminal.py              # 终端实时交互界面
└── clients/                      # 各模型适配客户端
    ├── __init__.py
    ├── asr_xfyun.py              # 讯飞 ASR 客户端（语音转文字）
    ├── llm_xfyun.py              # 讯飞 LLM 客户端（对话生成，流式）
    └── tts_xfyun.py              # 讯飞 TTS 客户端（文字转语音）
```

#### 3.3 src/OCR_agent/ — OCR 多 Agent 服务

```
OCR_agent/
├── __init__.py
├── config.py                     # OCR 配置（API 地址、模型名称、讯飞 LLM 密钥）
├── prompts.py                    # 三个 Agent 的系统提示词（Agent1 视觉提取、Agent2 专业分析、Agent3 通俗改写）
├── service.py                    # 多 Agent 编排（顺序执行 Agent1 → Agent2 → Agent3，结果清洗）
```

#### 3.4 src/RAG/ — 检索增强生成

```
RAG/
└── init.py                       # RAGStore 实现（向量检索、上下文拼接）
```

### 四、demo/ — 联调测试脚本

```
demo/
└── api_try/
    ├── __init__.py
    ├── test_backend_voice_api.py      # 语音接口联调
    ├── test_backend_ocr_api.py        # OCR 接口联调
    └── test_backend_concurrency.py    # 并发压测脚本（支持 text/voice/ocr/mixed 模式）
```

### 五、util/ — 独立工具

```
util/
├── condition.md                  # 跌倒检测算法判断条件说明（阈值、原理、C++ 实现摘要）
└── yolov8-pose-fall-detection/  # C++ YOLOv8-Pose 跌倒检测实现
    ├── include/                 # 头文件（BYTETracker、yolov8_pose、kalmanFilter 等）
    ├── src/                     # 源文件（追踪、姿态估计、卡尔曼滤波等）
    ├── test_data/               # 测试图片与视频
    ├── weights/                 # 优化后的模型权重（.bin + .param）
    └── CMakeLists.txt           # CMake 构建配置
```

### 六、models/ — 模型权重

```
models/
├── yolo11n-pose.pt              # YOLOv8-Pose Nano 权重（轻量级）
├── yolo11x-pose.pt              # YOLOv8-Pose Extra-Large 权重（高精度）
└── yolo26x-pose.pt              # YOLOv8-Pose 2.6x 权重
```

### 七、data/ — 静态数据

```
data/
└── qa.json                      # 问答对知识库（供 RAG 或其他模块使用）
```

### 八、顶层配置文件

```
.env                             # 根目录 .env（可选，通常直接使用 doc/.env）
.gitignore                       # Git 忽略配置
CLAUDE.md                        # Claude Code 项目级指令（若有）
```

---

## 模块依赖关系图

```
HTTP 请求
    │
    ▼
src/backend/main.py              # FastAPI 路由层
    │
    ├── /auth/*                 → UserService (src/backend/services.py)
    │                              └── SQLAlchemy → db/
    │
    ├── /chat/text              → VoiceAgentService (services.py)
    │                              └── VoicePipeline (voice_agent/pipeline.py)
    │                                    ├── ASR  → clients/asr_xfyun.py
    │                                    ├── LLM  → clients/llm_xfyun.py  ←── 讯飞星火 API
    │                                    └── TTS  → clients/tts_xfyun.py
    │                                    └── [可选] RAG → src/RAG/
    │
    ├── /chat/voice             → VoiceAgentService.voice_chat()
    │                              └── 同上 ASR + LLM + TTS 链路
    │
    └── /ocr/analyze             → OCRMultiAgentService (OCR_agent/service.py)
                                     ├── Agent1 (视觉) → OpenAI SDK → 火山引擎 Doubao
                                     ├── Agent2 (专业) → HTTP 流式 → 讯飞星火
                                     └── Agent3 (通俗) → HTTP 流式 → 讯飞星火
                                           └── [可选] TTS → clients/tts_xfyun.py
```