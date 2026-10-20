from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QObject, Qt, Signal, Slot

from desktop_app.class_names import load_class_names
from desktop_app.paths import OUTPUT_ROOT


def _aggregate_from_result(result) -> dict[int, int]:
    counts: dict[int, int] = defaultdict(int)
    if result.boxes is None or len(result.boxes) == 0:
        return dict(counts)
    cls = result.boxes.cls
    if hasattr(cls, "cpu"):
        cls = cls.cpu()
    for c in cls.int().tolist():
        counts[int(c)] += 1
    return dict(counts)


def _merge_counts(a: dict[int, int], b: dict[int, int]) -> dict[int, int]:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return out


class YoloWorker(QObject):
    """在同一线程中加载并运行 YOLO，避免跨线程 CUDA 问题。"""

    request_load = Signal(str)
    request_image = Signal(str, float, int)
    request_video = Signal(str, float, int)

    load_done = Signal(bool, str)
    image_done = Signal(dict)
    video_progress = Signal(int, int, str)
    video_done = Signal(dict)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self._model = None
        self.request_load.connect(self.load_model, Qt.ConnectionType.QueuedConnection)
        self.request_image.connect(self.predict_image, Qt.ConnectionType.QueuedConnection)
        self.request_video.connect(self.predict_video, Qt.ConnectionType.QueuedConnection)

    @Slot(str)
    def load_model(self, weight_path: str):
        try:
            from ultralytics import YOLO

            path = Path(weight_path)
            if not path.is_file():
                self.load_done.emit(False, f"未找到权重文件：{path}")
                return
            self._model = YOLO(str(path))
            warm = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model.predict(warm, verbose=False, conf=0.01)
            self.load_done.emit(True, "")
        except Exception as e:
            self._model = None
            self.load_done.emit(False, str(e))

    @Slot(str, float, int)
    def predict_image(self, image_path: str, conf: float, imgsz: int):
        if self._model is None:
            self.error.emit("模型未加载。")
            return
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project = OUTPUT_ROOT / "images"
            results = self._model.predict(
                source=image_path,
                conf=float(conf),
                imgsz=int(imgsz),
                save=True,
                project=str(project),
                name=stamp,
                exist_ok=True,
                verbose=False,
            )
            r0 = results[0]
            counts = _aggregate_from_result(r0)
            names = load_class_names()
            save_dir = Path(getattr(r0, "save_dir", "") or (project / stamp))
            annotated = None
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"):
                for p in save_dir.glob(ext):
                    annotated = str(p)
                    break
                if annotated:
                    break
            report = {
                "type": "image",
                "source": image_path,
                "counts": {str(k): v for k, v in counts.items()},
                "class_names": names,
                "annotated_path": annotated,
                "run_dir": str(save_dir),
            }
            (save_dir / "report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.image_done.emit(report)
        except Exception as e:
            self.error.emit(str(e))

    @Slot(str, float, int)
    def predict_video(self, video_path: str, conf: float, imgsz: int):
        if self._model is None:
            self.error.emit("模型未加载。")
            return
        cap = None
        writer = None
        try:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = OUTPUT_ROOT / "videos" / stamp
            run_dir.mkdir(parents=True, exist_ok=True)
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                self.error.emit("无法打开视频文件。")
                return
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            out_name = run_dir / f"{Path(video_path).stem}_detected.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(out_name), fourcc, float(fps), (w, h))
            if not writer.isOpened():
                self.error.emit("无法创建输出视频（编码器不可用）。")
                return
            counts: dict[int, int] = {}
            frame_idx = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_idx += 1
                if total > 0:
                    self.video_progress.emit(frame_idx, total, f"处理帧 {frame_idx}/{total}")
                else:
                    self.video_progress.emit(frame_idx, frame_idx, f"处理帧 {frame_idx}")
                res_list = self._model.predict(
                    source=frame,
                    conf=float(conf),
                    imgsz=int(imgsz),
                    verbose=False,
                )
                plot = res_list[0].plot()
                writer.write(plot)
                counts = _merge_counts(counts, _aggregate_from_result(res_list[0]))
            cap.release()
            cap = None
            writer.release()
            writer = None
            names = load_class_names()
            report = {
                "type": "video",
                "source": video_path,
                "output_video": str(out_name),
                "counts": {str(k): v for k, v in counts.items()},
                "class_names": names,
                "frames": frame_idx,
                "run_dir": str(run_dir),
            }
            (run_dir / "report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.video_done.emit(report)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if cap is not None:
                cap.release()
            if writer is not None:
                writer.release()
