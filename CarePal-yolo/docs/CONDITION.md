# CarePal 跌倒判定逻辑

本文档对应当前 Python 实现：`condition.py` 中的 `check_fall`，以及 `FallDetection.py` 中的数据集视频级判定策略。

## 1. 输入与坐标约定

- 输入关键点：COCO 17 点（索引 0~16），每个点使用 `(x, y)` 或 `(x, y, conf)`。
- 输入框：`bbox = [xmin, ymin, xmax, ymax]`。
- 图像坐标系：左上角是原点，`y` 越大表示位置越靠下。
- 单点有效性：`x > 0 且 y > 0`。

## 2. 辅助函数

### 2.1 `get_valid_point(kp_list, idx1, idx2)`

- 两点都有效：返回两点中心。
- 仅一点有效：返回该有效点。
- 两点都无效：返回 `None`。

用于生成：

- `c_ankle`（双脚踝中心或单脚踝）
- `c_hip`（双髋中心或单髋）
- `c_sh`（双肩中心或单肩）
- `c_knee`（双膝中心或单膝）

### 2.2 `calculate_angle(v1, v2)`

- 计算二维向量夹角（单位：度）。
- 若任一向量模长为 0，返回 `0.0`。

## 3. 帧级跌倒判定（`check_fall`）

判定方式是 **OR 关系**：5 个条件中任意一个满足即判定当前人体为跌倒，并立即返回。

## 3.1 Cond3：人体框宽高比

先判断包围框形态：

$$
aspect\_ratio = \frac{xmax - xmin}{ymax - ymin}
$$

当 `aspect_ratio > 0.90` 时，判定跌倒。

返回：`Cond3(AspectRatio>0.9)`

## 3.2 Cond1：肩膀高度与脚踝高度

前提：左右肩都有效，且 `c_ankle` 存在。

设：

- `min_shoulder_y = min(left_shoulder.y, right_shoulder.y)`

若 `min_shoulder_y >= c_ankle.y`，判定跌倒。

返回：`Cond1(Shoulder>=Ankle)`

## 3.3 Cond2：肩膀高度与膝盖高度

前提：左右肩、左右膝都有效。

设：

- `max_shoulder_y = max(left_shoulder.y, right_shoulder.y)`
- `min_knee_y = min(left_knee.y, right_knee.y)`

若 `max_shoulder_y > min_knee_y`，判定跌倒。

返回：`Cond2(Shoulder>Knee)`

## 3.4 Cond4：髋到膝连线与地面的夹角

前提：`c_hip` 存在，且左右膝都有效。

分别计算左/右膝相对 `c_hip` 的角度：

$$
theta_1 = |atan2(y_{lknee} - y_{hip}, x_{lknee} - x_{hip})|
$$

$$
theta_2 = |atan2(y_{rknee} - y_{hip}, x_{rknee} - x_{hip})|
$$

令：

- `min_theta = min(theta1, theta2)`
- `max_theta = max(theta1, theta2)`

若同时满足：

- `min_theta < 30.0`
- `max_theta < 70.0`

则判定跌倒。

返回：`Cond4(KneeHipAngle)`

## 3.5 Cond5：躯干与下肢关节角

前提：`c_sh`、`c_hip`、`c_knee`、`c_ankle` 均存在。

构造向量：

- `v1 = c_sh - c_hip`
- `v2 = c_knee - c_hip`
- `v3 = c_hip - c_knee`
- `v4 = c_ankle - c_knee`

角度：

- `theta3 = angle(v1, v2)`
- `theta4 = angle(v3, v4)`

若同时满足：

- `theta3 < 70.0`
- `theta4 < 30.0`

则判定跌倒。

返回：`Cond5(JointAngles)`

## 3.6 未命中条件

若 5 条规则均未命中，返回：`(False, "")`。

## 4. 视频级判定（数据集模式）

在 `FallDetection.py` 的 `dataset` 模式中：

- 每帧只要任意一个人被 `check_fall` 判为跌倒，则该帧计为 `fall frame`。
- 统计连续跌倒帧长度 `max_fall_streak`。
- 当 `max_fall_streak >= fall_streak_threshold`（默认 5）时，该视频预测为跌倒（`predicted_fall=1`），否则为非跌倒（`predicted_fall=0`）。

## 5. 规则执行顺序与特性

- 执行顺序固定：Cond3 -> Cond1 -> Cond2 -> Cond4 -> Cond5。
- 采用“先命中先返回”，所以返回的条件字符串表示首个触发条件。
- 当前规则为经验阈值法，优点是可解释性强、计算开销低；实际部署时可按场景调整阈值。
