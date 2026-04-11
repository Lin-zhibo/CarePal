# 技术文档

本文档说明当前后端系统的技术架构、并发处理策略、关键业务流程、部署与压测方法。

## 1. 系统架构

后端基于 FastAPI，整体分为三层：

1. API 层（`src/backend/main.py`）
   - 接收 HTTP 请求
   - 参数校验
   - 鉴权与响应封装

2. 业务层（`src/backend/services.py`）
   - 文本/语音会话管理
   - 会话记忆、压缩策略
   - prompt 业务规则

3. 模型适配层
   - 语音链路：`src/voice_agent/*`
   - OCR 多Agent：`src/OCR_agent/*`

## 2. 并发能力说明

### 2.1 已实现的并发处理

- 接口入口异步化：`chat/text`、`chat/voice`、`ocr/analyze`
- 阻塞任务放入线程池：
  - LLM/ASR/TTS 外部请求
  - OCR 多Agent模型调用
  - OCR->TTS 转换

### 2.2 会话并发安全

- 会话隔离维度：Bearer token
- 线程锁策略：
  - 同一 token 下请求串行（保证上下文顺序一致）
  - 不同 token 下请求并行

### 2.3 uvicorn worker 含义

- `worker` 是独立进程数（多进程并发）
- 每个 worker 都有自己的事件循环和线程池
- worker 越多，总吞吐通常越高，但内存占用也越高

建议：

- 开发：`--reload`（单 worker）
- 生产：`--workers 2` 或更高（按 CPU 核数与模型耗时调优）

## 3. 关键业务流程

### 3.1 语音对话流程

1. 前端上传音频（wav/mp3）
2. 后端识别音频格式并落盘
3. ASR 识别
4. LLM 生成
5. 按 `prompt` / `with_text` / `with_audio` 决策输出

### 3.2 OCR 流程

1. 前端上传 1~N 张图片
2. Agent1（视觉模型）提取关键信息
3. Agent2（LLM_MODEL）专业分析
4. Agent3（LLM_MODEL）通俗化
5. 清洗文本后返回，可选 TTS

## 4. 配置与环境变量

主要配置集中在 `doc/.env`：

- 讯飞语音：`XFYUN_*`
- OCR：`OCR_*`
- 通用 LLM：`LLM_MODEL`、`XFYUN_LLM_API_PASSWORD`
- 后端：`DATABASE_URL`、`JWT_*`

## 5. 并发测试脚本

脚本：`demo/api_try/test_backend_concurrency.py`

支持模式：

- `text`
- `voice`
- `ocr`
- `mixed`

关键参数：

- `--users` 并发用户数
- `--requests-per-user` 每用户请求数
- `--same-token` 是否共享 token（验证会话锁串行）

示例：

```bash
python demo/api_try/test_backend_concurrency.py --mode text --users 10 --requests-per-user 5
```

```bash
python demo/api_try/test_backend_concurrency.py --mode voice --audio demo/test.wav --users 5 --requests-per-user 2
```

```bash
python demo/api_try/test_backend_concurrency.py --mode ocr --images "img/img1.jpg,img/img2.jpg" --users 3 --requests-per-user 2
```

## 6. 可观测性建议

- 接入结构化日志（请求ID、token哈希、阶段耗时）
- 增加 metrics（p95/p99、错误率、队列长度）
- 对 OCR/语音重型任务可进一步做异步任务队列化
