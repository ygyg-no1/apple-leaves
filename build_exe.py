#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_exe.py —— 用 PyInstaller 把桌面客户端打包成 Windows 可执行程序
================================================================
产出：dist/AppleLeafDetector/AppleLeafDetector.exe（双击即可运行）
      —— 使用「目录模式(onedir)」：exe 与依赖分开放，启动快、便于替换权重。

【为什么用目录模式而不是单文件】
  本项目依赖 PyTorch 与 Ultralytics，体积很大。单文件模式每次启动都要把
  几百 MB 解压到临时目录，启动慢且容易被杀软拦截；目录模式启动快，
  也便于单独替换模型权重。

【运行前提（重要）】
  打包必须在 **Windows** 下用项目自带的虚拟环境执行，因为 PyInstaller
  不支持跨平台打包（Linux 上打不出 .exe）。本脚本会自动检测平台。

用法（在项目根目录、Windows 下执行）：
    .venv\\Scripts\\python.exe build_exe.py

常用参数：
    --model PATH     指定要随包分发的权重文件（默认自动查找）
    --name NAME      可执行文件名（默认 AppleLeafDetector）
    --console        保留控制台窗口（排查启动问题时可加）
    --clean          打包前清理旧的 build/dist
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_ENTRY = "run_desktop.py"
DEFAULT_NAME = "AppleLeafDetector"


def banner(t: str):
    print("\n" + "=" * 70)
    print(t)
    print("=" * 70)


def expected_classes() -> int:
    """从 datasets/data.yaml 读取期望的类别数（苹果叶病害应为 4）。"""
    try:
        import yaml
        d = yaml.safe_load((ROOT / "datasets" / "data.yaml").read_text(
            encoding="utf-8"))
        return int(d.get("nc") or len(d.get("names") or {}))
    except Exception:
        return 0


def try_load(path: Path) -> tuple[bool, int, str]:
    """尝试用 ultralytics 加载权重，返回 (是否可用, 类别数, 说明)。

    【为什么必须试加载】不同 YOLO 版本的权重不通用：
    例如 YOLOv13 的 .pt 含自定义模块 DSC3k2，用标准 ultralytics 加载会报
    "Can't get attribute 'DSC3k2'"。若不验证就打包，用户拿到 exe 会加载失败。
    """
    try:
        from ultralytics import YOLO
        m = YOLO(str(path))
        n = len(getattr(m, "names", {}) or {})
        return True, n, "可加载"
    except Exception as e:
        return False, 0, f"{type(e).__name__}: {str(e)[:70]}"


def find_model(explicit: str | None, expected_nc: int):
    """挑选权重：优先「能加载且类别数匹配」，其次「能加载」，最后给提示。

    返回 (选中路径 or None, 候选检查报告 list)
    """
    cands: list[Path] = []
    if explicit:
        cands.append(Path(explicit))
    # 仓库自带的权重
    cands.append(ROOT / "models" / "apple_leaf_best.pt")
    # 自己重新训练出来的权重
    cands += sorted(ROOT.glob("runs/**/best.pt"))
    # 其它预训练权重（备选，类别数与病害数据不匹配时会提示）
    cands += [ROOT / "yolov8n.pt", ROOT / "yolov13n.pt"]

    seen, report = set(), []
    ok_any, ok_match = None, None
    for c in cands:
        try:
            key = str(c.resolve())
        except Exception:
            continue
        if key in seen or not c.is_file() or c.stat().st_size < 100_000:
            continue
        seen.add(key)
        usable, nc, msg = try_load(c)
        report.append((c, usable, nc, msg))
        if usable:
            if ok_any is None:
                ok_any = c
            if expected_nc and nc == expected_nc and ok_match is None:
                ok_match = c
    return (ok_match or ok_any), report


def check_env(console: bool) -> bool:
    banner("① 环境检查")
    print(f"  操作系统 : {platform.system()} {platform.release()}")
    print(f"  Python   : {sys.version.split()[0]}  ({sys.executable})")
    if platform.system() != "Windows":
        print("\n  [警告] 当前不是 Windows。PyInstaller 不能跨平台打包，")
        print("         在 Linux 上生成的只能是 Linux 可执行文件，无法在 Windows 运行。")
        print("         请在 Windows 下用 .venv\\Scripts\\python.exe 运行本脚本。")
        return False
    ok = True
    for mod, name in [("PyInstaller", "PyInstaller"), ("PySide6", "PySide6"),
                      ("torch", "PyTorch"), ("ultralytics", "Ultralytics"),
                      ("cv2", "OpenCV"), ("yaml", "PyYAML")]:
        try:
            m = __import__(mod)
            v = getattr(m, "__version__", "")
            print(f"  [OK] {name:<12} {v}")
        except ImportError as e:
            ok = False
            print(f"  [缺失] {name:<12} {e}")
    if not ok:
        print("\n  请先安装缺失依赖，例如：")
        print("      .venv\\Scripts\\python.exe -m pip install pyinstaller "
              "PySide6 torch ultralytics opencv-python pyyaml")
    return ok


def write_spec(model: Path | None, name: str, console: bool,
               out_dir: Path, lean: bool = False) -> Path:
    """生成 PyInstaller spec 文件。"""
    # 【重要】datas 必须是真正的 Python 元组列表 (源路径, 目标目录)：
    #   1) 写成字符串字面量会报 "too many values to unpack (expected 2)"；
    #   2) 源路径必须是【确实存在】的文件，否则报
    #      "Unable to find ... when adding binary and data files"。
    # 因此这里先只声明一定存在的数据文件，权重稍后单独处理。
    datas = []
    if (ROOT / "datasets" / "data.yaml").is_file():
        datas.append(("datasets/data.yaml", "datasets"))
    if model is not None and model.is_file():
        datas.append((str(model), "models"))

    # 收集需要显式带入的隐藏导入与数据目录
    hiddenimports = [
        "ultralytics", "ultralytics.models", "ultralytics.nn",
        "ultralytics.utils", "cv2", "yaml", "torch", "torchvision",
        "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets",
        "matplotlib.backends.backend_qtagg", "desktop_app",
    ]
    # 【体积控制】collect_all 会把整包内容与全部子模块都塞进去。
    # PySide6 若整包收集，会带上 QtWebEngine / Qt3D / QtMultimedia 等
    # 用不到的模块，体积多出数百 MB。PyInstaller 自带的 PySide6 hook
    # 已能按实际 import 自动收集所需 Qt 模块，因此 --lean 模式下不整包收集。
    # torch 体积最大且其 hook 较完备，lean 模式下也不整包收集。
    if lean:
        collect_all = ["ultralytics", "cv2", "matplotlib"]
    else:
        collect_all = ["ultralytics", "torch", "torchvision", "cv2",
                       "matplotlib", "PySide6"]

    spec = f'''# -*- mode: python ; coding: utf-8 -*-
# 由 build_exe.py 自动生成 —— 请勿手工修改（改参数请重新运行 build_exe.py）
from PyInstaller.utils.hooks import collect_all, collect_data_files

datas = {datas!r}   # noqa: 见 build_exe.py，这里必须是元组列表
binaries = []
hiddenimports = {hiddenimports!r}

for pkg in {collect_all!r}:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:      # 某个包不可收集时跳过，不阻断整体构建
        print("collect_all 跳过", pkg, exc)

# ultralytics 的配置文件与字体等
try:
    datas += collect_data_files("ultralytics")
except Exception:
    pass

a = Analysis(
    [r"{APP_ENTRY}"],
    pathex=[r"{ROOT}"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "IPython", "jupyter", "notebook", "pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="{name}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console={console},
    icon=None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False, name="{name}",
)
'''
    spec_path = ROOT / f"{name}.spec"
    spec_path.write_text(spec, encoding="utf-8")
    print(f"  [spec] {spec_path}")
    return spec_path


def post_copy(model: Path | None, name: str):
    """把数据集配置与权重放到 exe 旁边，使 paths.py 的 parents[1] 能定位到。

    打包后 exe 位于 dist/<name>/<name>.exe，而 desktop_app/paths.py 用
    ROOT = Path(__file__).resolve().parents[1]，解包后 __file__ 在
    dist/<name>/_internal/desktop_app/paths.py，parents[1] 即 dist/<name>，
    因此 data.yaml 与权重需要放到 dist/<name>/ 下对应子目录。
    """
    dist = ROOT / "dist" / name
    if not dist.is_dir():
        print(f"  [警告] 未找到输出目录 {dist}")
        return
    # 数据配置
    src_yaml = ROOT / "datasets" / "data.yaml"
    if src_yaml.is_file():
        dst = dist / "datasets"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_yaml, dst / "data.yaml")
        print(f"  [复制] datasets/data.yaml -> {dst}")
    # 训练权重放到配置期望的位置
    if model is not None:
        wdir = dist / "models"
        wdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(model, wdir / "best.pt")
        print(f"  [复制] {model.name} -> {wdir / 'best.pt'}")
    (dist / "desktop_app_output").mkdir(parents=True, exist_ok=True)
    (dist / "desktop_app" / ".local_data").mkdir(parents=True, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=None, help="随包分发的权重文件路径")
    ap.add_argument("--name", default=DEFAULT_NAME, help="可执行文件名")
    ap.add_argument("--console", action="store_true", help="保留控制台窗口")
    ap.add_argument("--clean", action="store_true", help="打包前清理 build/dist")
    ap.add_argument("--lean", action="store_true",
                    help="精简体积：不整包收集 PySide6/torch，只带实际用到的部分")
    args = ap.parse_args()

    if not check_env(args.console):
        return 1

    banner("② 选择模型权重")
    exp_nc = expected_classes()
    print(f"  data.yaml 期望类别数: {exp_nc or '未知'}")
    model, report = find_model(args.model, exp_nc)
    if report:
        print("  候选权重可用性检查：")
        for c, usable, nc, msg in report:
            flag = "可用" if usable else "不可用"
            extra = f"类别数={nc}" if usable else msg
            print(f"    [{flag}] {c.relative_to(ROOT) if ROOT in c.parents else c}"
                  f"  {extra}")
    if model:
        print(f"\n  选中权重: {model}")
        print(f"  大小    : {model.stat().st_size/1024/1024:.1f} MB")
        # 说明是否与期望类别数匹配
        hit = [r for r in report if r[0] == model][0]
        if exp_nc and hit[2] != exp_nc:
            print(f"  [重要] 该权重类别数为 {hit[2]}，与 data.yaml 的 {exp_nc} 不一致！")
            print("         这会导致检测结果与病害类别对不上。")
            print("         请把训练好的 4 类权重 best.pt 放到：")
            print(f"           {(ROOT / 'models/apple_leaf_best.pt')}")
            print("         然后重新运行本脚本打包。")
    else:
        print("  [警告] 未找到任何可加载的权重，打包后需手动放置权重才能检测。")

    if args.clean:
        banner("③ 清理旧构建")
        for d in ("build_exe_work", "dist"):
            p = ROOT / d
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                print(f"  已删除 {p}")

    banner("④ 准备权重到配置路径")
    # desktop_app/paths.py 里 DEFAULT_MODEL 指向
    #   models/apple_leaf_best.pt
    # 若该文件不存在，就把选中的权重复制过去，避免"找不到模型"。
    # 若已存在（说明有训练好的模型），则完全不改动。
    wanted = ROOT / "models" / "apple_leaf_best.pt"
    if wanted.is_file():
        usable, nc, msg = try_load(wanted)
        print(f"  配置路径已有权重: {wanted}")
        print(f"  （大小 {wanted.stat().st_size/1024/1024:.1f} MB，"
              f"{'可加载' if usable else '不可加载：' + msg}）")
        if not usable:
            print("  [重要] 该权重当前无法被 ultralytics 加载，")
            print("         请替换为可用的训练权重后重新打包。")
    elif model is not None:
        wanted.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(model, wanted)
        print(f"  配置路径无权重，已复制 {model.name} -> {wanted}")
    else:
        print("  [警告] 无可用权重，程序启动后将无法加载模型。")

    banner("⑤ 生成 spec")
    spec = write_spec(model, args.name, args.console, ROOT / "dist",
                      lean=args.lean)

    banner("⑥ 运行 PyInstaller（首次打包可能需要 5~20 分钟）")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm",
           "--distpath", str(ROOT / "dist"),
           "--workpath", str(ROOT / "build_exe_work"),
           str(spec)]
    print("  $ " + " ".join(cmd) + "\n")
    # 不加 capture_output：让 PyInstaller 的实时输出直接显示在终端，
    # 便于观察进度与排查错误（早期版本把它吞掉了，出错时看不到原因）。
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        print(f"\n  [失败] PyInstaller 退出码 {r.returncode}")
        return r.returncode

    banner("⑦ 布置运行时文件")
    post_copy(model, args.name)

    exe = ROOT / "dist" / args.name / f"{args.name}.exe"
    banner("完成")
    if exe.is_file():
        size = sum(f.stat().st_size for f in exe.parent.rglob("*")
                   if f.is_file())
        print(f"  可执行文件: {exe}")
        print(f"  整个目录  : {size/1024/1024:.0f} MB")
        print("\n  分发方式：把整个 dist\\" + args.name + " 文件夹拷给用户，")
        print("           双击其中的 " + args.name + ".exe 即可运行。")
    else:
        print(f"  [警告] 未找到 {exe}，请检查上面的构建输出。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
