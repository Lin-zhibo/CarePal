# STGCN 跌倒检测模块

## 概述

STGCN (Spatial-Temporal Graph Convolutional Network) 基于人体 17 骨骼关键点序列进行跌倒检测。

- **输入**: [B, T, V, C] 滑动窗口 (T=帧数, V=节点数=17, C=x,y,conf)
- **输出**: [B, num_classes] 正常/跌倒 概率

点和边由 YOLO-Pose 检测提供，只有人是否跌倒的标签来自数据集标注文件。

## 空间图卷积实现（标准 ST-GCN）

当前实现采用标准分区邻接形式：

- 邻接矩阵 `A` 形状为 `[K, V, V]`，其中 `K=3`：`self-link / inward / outward`
- 空间卷积计算流程：
    1. 输入 `x: [B, C_in, T, V]`
    2. `1x1 Conv` 后为 `[B, C_out*K, T, V]`
    3. reshape 为 `[B, K, C_out, T, V]`
    4. 与 `A[K,V,V]` 聚合后输出 `[B, C_out, T, V]`
- 每个 ST-GCN block 都有独立的 `edge_importance`（形状与 `A` 相同）

说明：旧版 checkpoint 与当前结构不完全兼容，建议使用当前代码重新训练得到新权重。

## 超参数说明

| 参数                            | 默认值       | 说明                            |
| ------------------------------- | ------------ | ------------------------------- |
| `STGCN_in_channels`           | 3            | 输入特征维度 (x, y, confidence) |
| `STGCN_num_classes`           | 2            | 输出类别数 (0=正常, 1=跌倒)     |
| `STGCN_window_size`           | 30           | 滑动窗口帧数                    |
| `STGCN_stride`                | 15           | 滑动窗口步长                    |
| `STGCN_hidden_dims`           | [64,128,256] | 各 ST-GCN Block 的隐层维度      |
| `STGCN_dropout`               | 0.5          | Dropout 比例                    |
| `STGCN_epochs`                | 100          | 训练轮数                        |
| `STGCN_batch_size`            | 32           | 批大小                          |
| `STGCN_lr`                    | 0.001        | 学习率                          |
| `STGCN_n_folds`               | 5            | K折交叉验证折数                 |
| `STGCN_fall_streak_threshold` | 5            | 判定跌倒视频的最小连续跌倒帧数  |

## COCO 17 点骨骼连接

```
0=nose, 1=left_eye, 2=right_eye, 3=left_ear, 4=right_ear,
5=left_shoulder, 6=right_shoulder, 7=left_elbow, 8=right_elbow,
9=left_wrist, 10=right_wrist,
11=left_hip, 12=right_hip,
13=left_knee, 14=right_knee,
15=left_ankle, 16=right_ankle
```

边连接:

```
(0,1), (0,2), (1,3), (2,4),       # 头-眼-耳
(5,6),                             # 肩宽
(5,7), (7,9),                      # 左臂
(6,8), (8,10),                     # 右臂
(5,11), (6,12),                    # 躯干
(11,12),                           # 髋宽
(11,13), (13,15),                  # 左腿
(12,14), (14,16),                  # 右腿
```

## 数据集标注格式

| 数据集     | 目录                                      | 帧级标注 | 标注格式                                 |
| ---------- | ----------------------------------------- | -------- | ---------------------------------------- |
| GMDCSA24   | .../Subject N/ADL/ 或 Fall/               | 有       | CSV 时间段 `Falling[3.4 to 6]` → 转帧 |
| IMVIA/Le2i | .../场景名/Annotation_files/video (N).txt | 有       | 第1-2行=跌倒起止帧号                     |
| UR-Fall    | .../adl-N/ 或 fall-N/（PNG序列）          | 无       | 文件夹名 adl/fall=视频级标签             |

## 关键点缓存两阶段流程

为加速重复训练/评估，YOLO 关键点抽取结果会缓存到本地磁盘。

### 缓存目录结构

```
/tmp/ne/
├── gmdcsa24/
│   └── <hash>.npz
├── imvia/
│   └── <hash>.npz
└── urfall/
    └── <hash>.npz
```

### npz 缓存内容

| key | 形状 | 说明 |
|-----|------|------|
| `keypoints` | `[T, 17, 3]` | 关键点序列 |
| `img_size` | `(width, height)` | 视频尺寸 |
| `task_desc` | `str` | `gmdcsa24` / `imvia` / `urfall` |
| `label` | `0/1` | 视频级标签 |
| `fall_start` | `int\|None` | 跌倒起始帧 |
| `fall_end` | `int\|None` | 跌倒结束帧 |
| `source_path` | `str` | 原始路径 |

### 使用方式

```bash
# 阶段1：独立抽取关键点（仅需运行一次）
python extract.py --datasets <roots> --cache-dir /tmp/ne

# 阶段2：训练时自动命中缓存
python train_stgcn.py --cache-dir /tmp/ne

# 强制重建缓存（如数据集更新）
python train_stgcn.py --cache-dir /tmp/ne --force-cache
```

- 缓存未命中时自动回退 YOLO 抽取并写回缓存
- 评估时同样自动命中缓存
- camera 模式不涉及缓存（实时流无法缓存）

### 配置项

在 `config/models.json` 中设置：

```json
{
    "cache_dir": "/tmp/ne",
    "cache_force_rebuild": false
}
```

## 运行示例

```bash
# 训练（K折交叉验证 + 全量训练，输出到 out/<timestamp>/）
python train_stgcn.py

# 摄像头实时检测（STGCN 神经网络）
python pipeline.py --mode camera --source 0 --method stgcn \
    --model out/20240422_120000/models/best_model.pth

# 摄像头实时检测（几何条件）
python pipeline.py --mode camera --source 0 --method geometric

# 数据集评估（支持 GMDCSA24 / IMVIA / UR-Fall）
python pipeline.py --mode dataset \
    --source dataset/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos-v2.1 \
    --method stgcn --model out/20240422_120000/models/best_model.pth
```

## 训练输出结构

```
out/<timestamp>/
├── models/
│   ├── fold1_best.pth    # 各折最优模型
│   ├── fold2_best.pth
│   └── best_model.pth     # 全量训练最优模型
├── img/
│   └── metrics.png        # loss/precision/recall/F1 曲线
└── output.txt            # 测试集视频级评估结果
```

## 验证方式

```bash
# 1. 验证 STGCN 模型可加载
python -c "from STGCN import STGCN_FallDetection; m = STGCN_FallDetection(); print('STGCN OK')"

# 2. 验证 pipeline 可运行（几何条件，摄像头）
python pipeline.py --mode camera --source 0 --method geometric --no-show

# 3. 验证数据集评估
python pipeline.py --mode dataset --source dataset/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos-v2.1 --method geometric --no-show
```
