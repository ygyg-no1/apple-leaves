"""
苹果叶病变检测 — 桌面客户端入口。

运行（需在项目根目录、已安装依赖）:
    python run_desktop.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from desktop_app.paths import OUTPUT_ROOT


def _fail_missing_torch() -> int:
    exe = Path(sys.executable)
    msg = (
        "当前解释器未安装 PyTorch（import torch 失败），因此无法加载 YOLO 权重。\n\n"
        "请在「用于启动本程序的同一个 Python」里安装依赖，例如：\n"
        f"  \"{exe}\" -m pip install torch ultralytics opencv-python\n\n"
        "若只要 CPU 推理，可先装官方 CPU 轮子再装其余包：\n"
        f"  \"{exe}\" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu\n"
    )
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication(sys.argv)
        QMessageBox.critical(None, "缺少依赖：torch", msg)
    except Exception:
        print(msg, file=sys.stderr)
    return 1


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        import torch  # noqa: F401
    except ImportError:
        return _fail_missing_torch()
    from desktop_app.main_ui import run_application

    return run_application()


if __name__ == "__main__":
    raise SystemExit(main())
