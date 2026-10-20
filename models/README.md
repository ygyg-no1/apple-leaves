# 模型说明

| 项 | 内容 |
|---|---|
| 文件 | `apple_leaf_best.pt` |
| 用途 | 苹果叶片病害检测（4 类：黑腐 / 锈病 / 健康 / 疮痂） |
| 输入 | 图像，推理时缩放至 640×640 |
| 输出 | 边界框 + 类别 + 置信度 |
| 来源 | 本仓库 `train.py` 在同一苹果叶数据集上微调得到 |

使用：

```python
from ultralytics import YOLO
model = YOLO("models/apple_leaf_best.pt")
results = model.predict("your_image.jpg", imgsz=640, conf=0.25)
```

说明：

- 权重在训练集所在的采集条件（单一产地、单一光照条件）下表现最好，**跨域泛化未验证**。
- 类别顺序以权重内置的 `model.names` 为准；若与 `datasets/data.yaml` 不一致，桌面端会显示错的类别名，请以 `model.names` 为准。
- 原始训练权重文件与训练日志不随仓库分发。
