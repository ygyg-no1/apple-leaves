"""
统一路径定义。

【为什么需要区分「源码运行」与「打包成 exe 运行」】
  源码运行时，本文件在 <项目根>/desktop_app/paths.py，向上两级即项目根，
  因此可以直接用 __file__ 推导。
  但用 PyInstaller 打包后，本文件会被放进
      dist/AppleLeafDetector/_internal/desktop_app/paths.py
  此时再用 __file__ 推导，得到的根目录会落在 _internal 里，
  导致找不到 datasets/data.yaml 与模型权重。
  因此打包运行（sys.frozen）时改用 exe 所在目录作为根目录。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _detect_root() -> Path:
    """推导项目根目录（兼容源码运行与 PyInstaller 打包运行）。"""
    if getattr(sys, "frozen", False):
        # 打包运行：以可执行文件所在目录为根
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


ROOT = _detect_root()

# 权重默认放在 models/ 下（仓库自带一个 4 类苹果叶模型），
# 也可以用环境变量 ALD_MODEL 指向任意权重。
DEFAULT_MODEL = Path(os.environ.get("ALD_MODEL", ROOT / "models" / "apple_leaf_best.pt"))
DATA_YAML = ROOT / "datasets" / "data.yaml"
APP_LOCAL_DIR = ROOT / "desktop_app" / ".local_data"
OUTPUT_ROOT = ROOT / "desktop_app_output"
