# STGCN 训练项目 - 修复完成

## 已完成修复

1. **时间卷积方向** (`STGCN.py:113`)
   - 修复前：`kernel_size=(1, kernel_size)` — 沿 V（节点）维度卷积
   - 修复后：`kernel_size=(kernel_size, 1)` — 沿 T（时间）维度卷积
   - padding 相应调整：`(0, pad)` → `(pad, 0)`

2. **类别不平衡** (`train_stgcn.py:364, 401`)
   - 修复前：`nn.CrossEntropyLoss()`
   - 修复后：`nn.CrossEntropyLoss(weight=torch.tensor([1.0, 3.0]).to(device))`
   - fall 类权重 3.0，提升跌倒召回

3. **UnicodeDecodeError** (`STGCN.py:321`)
   - 修复前：`open(txt_path, "r")` 默认 GBK 编码
   - 修复后：`open(txt_path, "r", encoding="utf-8", errors="replace")`

4. **坐标归一化硬编码** (`train_stgcn.py`)
   - 修复前：所有数据使用固定 `img_size=(640, 640)` 归一化，跨数据集失真
   - 修复后：
     - 新增 `get_video_dimensions()` 函数，从视频/图像元数据获取实际尺寸
     - `scan_datasets()` 返回 `img_sizes` 字典，映射 video_path → (width, height)
     - `WindowDataset` 改为接收 `img_sizes` 字典，在 `__getitem__` 中查表使用真实尺寸
     - `build_window_dataset` 增加 `video_path` 参数，传递给窗口元组

5. **人物选择 kp[0]** (`train_stgcn.py:70-96, 99-122`, `evaluate.py:49-71, 74-91`)
   - 修复前：始终取 `kp[0]`（第一人），多人物场景选错人引入噪声
   - 修复后：选择检测框置信度最高的人 `best_idx = np.argmax(scores)`
   - 影响函数：`extract_keypoints`, `extract_keypoints_from_images` (train + evaluate)

6. **KFold 数据泄漏** (`train_stgcn.py:376-380`)
   - 修复前：`KFold(shuffle=True)` 随机切分窗口，同一视频的相邻窗口分散在训练/验证集
   - 修复后：使用 `GroupKFold(groups=video_ids)` 按视频分组，保证同一视频的所有窗口在同一折

---

## 已同步：STGCN 架构对齐原论文（10层）+ 双流 Model

### 实施结论

`STGCN.py` 已对齐原论文示例层结构，并完成双流 ST-GCN：

- 单流主干 `ST_GCN` 采用固定 10 层：
  `64,64,64,64,128,128,128,256,256,256`
- 时序下采样在第 5、8 层（`stride=2`），其余层 `stride=1`
- 空间图卷积保持标准分区邻接 `A[K,V,V]`，`K=3`（`self/inward/outward`）
- 每层保留独立 `edge_importance` 参数（形状同 `A`）
- 新增双流 `Model`：
  - `origin_stream` 使用原始骨架序列
  - `motion_stream` 使用中心差分运动序列
  - 两流 logits 相加作为最终输出

### 与工程接口对齐

- `STGCN_FallDetection` 外部接口保持不变：
  - 输入 `[B, T, V, C]`
  - 内部转换为 `[N, C, T, V, M=1]` 后送入双流 `Model`
  - 输出 `[B, num_classes]`
- `hidden_dims` 不再用于自定义网络深宽：仅允许 `None` 或 `[64, 128, 256]`，否则抛错提示固定论文结构。

### 维度匹配检查

1. 单流 `ST_GCN`
   - 输入：`[N, C, T, V, M]`
   - 经过 data BN + 10 层 ST-GCN 后：`[N*M, 256, T', V]`
   - 全局池化 + 分类后：`[N, num_class]`

2. 双流 `Model`
   - 输入：`[N, C, T, V, M]`
   - 运动流序列：`m[:, :, 1:-1] = x[:, :, 1:-1] - 0.5*x[:, :, 2:] - 0.5*x[:, :, :-2]`
   - 输出：`origin_stream(x) + motion_stream(m)`，形状 `[N, num_class]`

3. 包装层 `STGCN_FallDetection`
   - 输入：`[B, T, V, C]`
   - 输出：`[B, num_classes]`
   - 增加维度/通道/关键点数量检查，避免静默错配。

### 兼容性说明

- 主干结构已固定为论文版 10 层，旧 checkpoint 可能不兼容。
- `STGCN_Pipeline` 已在加载失败时给出明确提示：请使用新架构重新训练权重。

### 已完成验证

1. `STGCN_FallDetection` 随机输入前向输出 `(2, 2)`，反向传播成功。
2. 双流 `Model` 随机输入前向输出 `(2, 2)`。

---

## 待实施计划：关键点抽取缓存化（记录于 2026-04-23）

### 目标

将当前“训练/评估时实时抽取关键点”的流程改造为“两阶段流程”：

1. 先通过 `extract.py` 独立抽取关键点并缓存到 `/tmp/ne`
2. `train_stgcn.py` 与 `evaluate.py` 优先读取缓存，避免重复抽取

### 已确认决策

1. 缓存格式使用 `npz`
2. 缓存目录使用 `/tmp/ne`
3. 训练阶段缓存缺失时：自动回退在线抽取，并写回缓存
4. 评估阶段同样接入缓存读取与回退机制

### 实施步骤

1. 在 `extract.py` 实现独立抽取入口
   - 复用现有视频抽取与图像序列抽取逻辑
   - 复用视频/图像尺寸获取逻辑
2. 在 `extract.py` 增加统一任务扫描
   - GMDCSA24: 复用 `trainSTGCN/train_GMDCSA24.py`
   - IMVIA/Le2i: 复用 `trainSTGCN/train_Le2i.py`
   - UR-Fall: 扫描 `*-cam0-rgb` 图像序列目录
3. 在 `extract.py` 增加 CLI（仅抽取模式）
   - 默认输出 `/tmp/ne`
   - 支持“已存在缓存跳过”与“强制重建”
4. 改造 `train_stgcn.py`
   - 数据准备阶段优先读缓存
   - 缓存缺失时回退在线抽取并写回
   - 保持窗口标签构造与 GroupKFold 分组逻辑不变
5. 改造 `evaluate.py`
   - 视频级评估时优先读取缓存关键点
   - 缺失时回退在线抽取并写回
   - 保持 streak 判定逻辑不变
6. 配置与文档更新
   - 在 `config/models.json` 增加缓存相关配置项
   - 在 `docs/STGCN.md` 增加“先抽取再训练/评估”流程说明

### 缓存内容约定（单个 npz）

- `keypoints`: `[T, 17, 3]`
- `img_size`: `(width, height)`
- `task_desc`: `gmdcsa24/imvia/urfall`
- `label`: `0/1`
- `fall_start`, `fall_end`: 帧级区间（若无则为空）
- `source_path`: 原始输入路径

### 验收标准

1. 可独立执行 `extract.py`，并在 `/tmp/ne` 生成缓存
2. 训练冷启动时可自动回退抽取并写回缓存
3. 同配置重复训练时缓存命中显著提升、回退次数显著下降
4. 改造前后窗口总数与标签分布一致
5. 评估脚本可命中缓存且输出格式保持兼容
