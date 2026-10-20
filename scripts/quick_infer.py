"""最小推理示例：用仓库自带的权重跑一遍验证集。

用法:
    python scripts/quick_infer.py [图片目录] [权重路径]
"""
import sys
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parents[1]
weights = sys.argv[2] if len(sys.argv) > 2 else ROOT / "models" / "apple_leaf_best.pt"
source = sys.argv[1] if len(sys.argv) > 1 else ROOT / "datasets" / "images" / "val"

model = YOLO(str(weights))
model.predict(source=str(source), imgsz=640, conf=0.25, save=True)
