# 数据集说明

仓库只保留数据集定义 `data.yaml`，**不包含图像与标注**。

## 目录约定（YOLO 检测格式）

```
datasets/
├── data.yaml
├── images/
│   ├── train/    # *.jpg / *.png
│   └── val/
└── labels/
    ├── train/    # 与图像同名的 *.txt，每行: class cx cy w h（相对坐标 0~1）
    └── val/
```

## 类别

```yaml
nc: 4
names:
  0: Apple__BlackRot
  1: Apple__CedarRust
  2: Apple__Healthy
  3: Apple__Scab
```

## 采集与标注建议

- 单叶 / 单枝 / 整树三种尺度都要有，避免只拍特写导致真实场景漏检
- 病斑与健康叶片同时标，负样本（纯健康）也要进验证集
- 同一张原图的裁剪不要同时出现在训练集与验证集，否则指标会虚高

## 授权

自建数据集；引用第三方图像（如公开植物病害数据集）时请遵守其原始许可，并在论文/说明中注明来源。
