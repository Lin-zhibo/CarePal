"""一个简单的 YOLO 姿态检测脚本。

运行前请先安装依赖：
pip install ultralytics opencv-python
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Union

import cv2

# 确保日志目录存在
Path("log").mkdir(parents=True, exist_ok=True)

# 配置日志记录
logging.basicConfig(
	level=logging.INFO,
	format="%(asctime)s [%(levelname)s] %(message)s",
	handlers=[
		logging.StreamHandler(),
		logging.FileHandler("log/log.log", encoding="utf-8"),
	],
)
logger = logging.getLogger(__name__)

try:
	from ultralytics import YOLO
except ImportError as exc:
	raise ImportError(
		"未检测到 ultralytics，请先执行: pip install ultralytics opencv-python"
	) from exc


def load_config(config_path: str) -> Dict[str, Any]:
	"""功能:
		从 JSON 配置文件加载模型配置。

	输入参数:
		config_path (str): 配置文件路径。

	返回值:
		Dict[str, Any]: 包含 model 和 models_dir 的配置字典。
	"""
	with open(config_path, "r", encoding="utf-8") as f:
		return json.load(f)


def parse_args() -> argparse.Namespace:
	"""功能:
		解析命令行参数，生成姿态检测配置。

	输入参数:
		无。

	返回值:
		argparse.Namespace: 包含模型路径、输入源、阈值和可视化等配置项。
	"""
	parser = argparse.ArgumentParser(description="使用 YOLO11 执行姿态检测")
	parser.add_argument(
		"--config",
		type=str,
		default="config/models.json",
		help="模型配置文件路径，默认使用 config/models.json",
	)
	parser.add_argument(
		"--source",
		type=str,
		default="0",
		help="输入源，可传图片/视频路径、目录、URL，或摄像头编号(例如 0)",
	)
	parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
	parser.add_argument("--iou", type=float, default=0.7, help="NMS 的 IOU 阈值")
	parser.add_argument("--imgsz", type=int, default=640, help="推理尺寸")
	parser.add_argument(
		"--device",
		type=str,
		default="0",
		help="推理设备，例如 cpu、0、0,1；默认使用第一块 GPU (0)",
	)
	parser.add_argument(
		"--no-show",
		action="store_true",
		help="关闭实时显示窗口（默认会弹窗显示姿态识别效果）",
	)
	parser.add_argument("--save", action="store_true", help="保存检测结果")
	parser.add_argument(
		"--project",
		type=str,
		default="runs/pose",
		help="结果保存目录的项目名",
	)
	parser.add_argument(
		"--name",
		type=str,
		default="predict",
		help="结果保存目录的实验名",
	)
	return parser.parse_args()


def parse_source(source: str) -> Union[int, str]:
	"""功能:
		将输入源字符串转换为 YOLO 可识别的格式。

	输入参数:
		source (str): 用户输入的数据源字符串，可为摄像头编号或文件路径/URL。

	返回值:
		Union[int, str]: 若输入是纯数字则返回摄像头索引(int)，否则返回规范化后的路径或URL字符串。
	"""
	if source.isdigit():
		return int(source)
	return str(Path(source).expanduser())


def ensure_model_in_models_dir(model_path: str, models_dir: str) -> Path:
	"""功能:
		确保姿态模型最终保存在指定的 models 目录中。

	输入参数:
		model_path (str): 用户输入的模型路径、模型名或下载地址。
		models_dir (str): 模型目标保存目录路径。

	返回值:
		Path: 已确认存在于 models 目录下的模型文件路径。
	"""
	models_root = Path(models_dir).expanduser()
	models_root.mkdir(parents=True, exist_ok=True)

	input_path = Path(model_path).expanduser()
	model_name = Path(model_path.split("?")[0]).name or "yolo11n-pose.pt"
	target_path = models_root / model_name

	if target_path.exists():
		return target_path

	if input_path.exists():
		if input_path.resolve() != target_path.resolve():
			shutil.copy2(input_path, target_path)
		return target_path

	# 通过 YOLO 加载触发自动下载，再将权重移动到 models 目录。
	temp_model = YOLO(model_path)
	resolved_ckpt = Path(str(getattr(temp_model, "ckpt_path", model_path))).expanduser()

	if resolved_ckpt.exists() and resolved_ckpt.resolve() != target_path.resolve():
		shutil.move(str(resolved_ckpt), str(target_path))

	if not target_path.exists():
		raise FileNotFoundError(f"未能将模型保存到目录: {target_path}")

	return target_path


def load_pose_model(model_path: str, models_dir: str) -> YOLO:
	"""功能:
		加载 YOLO 姿态检测模型，并确保模型文件保存在 models 目录。

	输入参数:
		model_path (str): 模型权重路径或模型名称（例如 yolo11n-pose.pt）。
		models_dir (str): 模型保存目录路径。

	返回值:
		YOLO: 已加载完成、可直接执行推理的 YOLO 模型实例。
	"""
	final_model_path = ensure_model_in_models_dir(model_path=model_path, models_dir=models_dir)
	return YOLO(str(final_model_path))


def run_pose_detection(
	model: YOLO,
	source: Union[int, str],
	conf: float,
	iou: float,
	imgsz: int,
	device: Optional[str],
	show: bool,
	save: bool,
	project: str,
	name: str,
) -> Sequence[Any]:
	"""功能:
		使用 YOLO 模型对输入源执行姿态检测。

	输入参数:
		model (YOLO): 已加载的 YOLO 姿态模型。
		source (Union[int, str]): 输入源，可为摄像头索引或图片/视频/URL。
		conf (float): 目标置信度阈值。
		iou (float): 非极大值抑制使用的 IOU 阈值。
		imgsz (int): 推理时的输入尺寸。
		device (Optional[str]): 推理设备标识，None 表示自动选择。
		show (bool): 是否实时显示可视化结果窗口。
		save (bool): 是否将推理结果保存到磁盘。
		project (str): 结果保存项目目录名。
		name (str): 结果保存实验目录名。

	返回值:
		Sequence[Any]: 每一帧或每一张图片的检测结果集合。
	"""
	# 判断是否为摄像头输入（整数索引）或视频流
	is_live = isinstance(source, int) or (isinstance(source, str) and source.isdigit())

	predict_kwargs: Dict[str, Any] = {
		"source": source,
		"conf": conf,
		"iou": iou,
		"imgsz": imgsz,
		"show": show,
		"save": save,
		"project": project,
		"name": name,
		"verbose": False,
		"stream": is_live,
	}
	if device is not None:
		predict_kwargs["device"] = device

	results = model.predict(**predict_kwargs)
	
	if is_live:
		results_list = []
		for r in results:
			results_list = [r]
			if show and cv2.waitKey(1) & 0xFF == 27:
				break
		return results_list

	return results


def summarize_results(results: Sequence[Any]) -> Dict[str, Any]:
	"""功能:
		对推理结果做简要统计，便于快速查看检测效果。

	输入参数:
		results (Sequence[Any]): YOLO 推理返回的结果序列。

	返回值:
		Dict[str, Any]: 包含结果数量、首帧目标数和关键点张量形状等统计信息。
	"""
	summary: Dict[str, Any] = {
		"result_count": len(results),
		"first_frame_person_count": 0,
		"first_frame_keypoint_shape": (0, 0, 0),
	}

	if not results:
		return summary

	first = results[0]
	if getattr(first, "boxes", None) is not None:
		summary["first_frame_person_count"] = len(first.boxes)

	keypoints = getattr(first, "keypoints", None)
	if keypoints is not None and getattr(keypoints, "xy", None) is not None:
		summary["first_frame_keypoint_shape"] = tuple(int(v) for v in keypoints.xy.shape)

	return summary


def main() -> None:
	"""功能:
		串联参数解析、模型加载、姿态检测与结果摘要打印，作为脚本入口。

	输入参数:
		无。

	返回值:
		None: 该函数仅执行流程并在控制台输出结果摘要。
	"""
	args = parse_args()

	# 从配置文件加载模型配置
	logger.info(f"正在加载配置: {args.config}")
	config = load_config(args.config)
	model_path = config.get("model", "yolo11x-pose.pt")
	models_dir = config.get("models_dir", "models")

	logger.info(f"使用的模型: {model_path} (存放目录: {models_dir})")
	source = parse_source(args.source)
	model = load_pose_model(model_path=model_path, models_dir=models_dir)
	
	device_used = args.device if args.device else "auto (由 YOLO 决定)"
	logger.info(f"运行设备: {device_used}")
	logger.info(f"输入源: {source}")
	show_window = not args.no_show

	results = run_pose_detection(
		model=model,
		source=source,
		conf=args.conf,
		iou=args.iou,
		imgsz=args.imgsz,
		device=args.device,
		show=show_window,
		save=args.save,
		project=args.project,
		name=args.name,
	)

	summary = summarize_results(results)
	logger.info("姿态检测完成。")
	logger.info(f"结果数量: {summary['result_count']}")
	logger.info(f"首帧人体数量: {summary['first_frame_person_count']}")
	logger.info(f"首帧关键点形状: {summary['first_frame_keypoint_shape']}")


if __name__ == "__main__":
	main()
