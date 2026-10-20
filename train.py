import warnings

warnings.filterwarnings('ignore')
from ultralytics import YOLO

if __name__ == '__main__':
    # 改用YOLOv8 medium模型（确保与库版本兼容）
    model = YOLO('yolov8n.pt')  # 自动下载官方预训练权重，避免路径问题

    model.train(
        data='datasets/data.yaml',  # 相对项目根目录
        cache=True,
        imgsz=640,
        epochs=50,
        batch=-1,  # 自动计算最大批次，适配RTX5060显存
        close_mosaic=100,  # 延后关闭Mosaic增强
        mosaic=0.3,  # 降低Mosaic概率
        # 移除blur、rotate、label_smoothing等无效参数
        hsv_h=0.02,  # HSV调整参数有效，可保留
        hsv_s=0.6,
        hsv_v=0.5,
        flipud=0.2,  # 部分版本支持直接传，若仍报错则移至data.yaml
        fliplr=0.5,
        workers=2,
        device='0',
        patience=20,  # 早停策略有效
        optimizer='AdamW',  # 有效参数
        lr0=0.001,
        lrf=0.01,
        amp=True,  # 开启混合精度训练
        weight_decay=0.0005,  # 有效参数，增强正则化
        project='runs/train',
        name='apple_leaf_det',
        exist_ok=True  # 允许覆盖旧实验，方便调试
    )