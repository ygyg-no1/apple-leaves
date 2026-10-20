# 苹果叶病害智能检测系统

基于 Ultralytics YOLO 目标检测管线与 PySide6 的桌面端苹果叶片病害检测工具：加载图像/视频，输出病斑边界框与四类病害标签（黑腐 / 锈病 / 健康 / 疮痂），统计各类别数量并导出柱状图；可选接入大语言模型接口，把检测统计转成中文植保建议（辅助文字，不参与视觉判别）。

> 本项目为教学 / 竞赛 / 课程设计用途的实现示例，**未经植保部门验证，不能替代现场农技诊断**。药物使用请遵守当地法规与农药标签。

## 功能

- 桌面工作站（PySide6）：模型加载、单图 / 批量 / 视频推理、阈值调节、结果叠加显示
- 检测统计与图表：按类别计数、置信度分布、图表导出
- 本地账号登录（密码 PBKDF2 加盐哈希，仅本地存储）
- 可选：调用 DeepSeek 兼容接口生成中文防治建议（需自备 API Key，通过界面或环境变量配置，不写入仓库）
- 一键打包 Windows 可执行程序（PyInstaller 脚本）

## 目录结构

```
.
├── desktop_app/              # 桌面客户端（界面、推理线程、图表、登录、路径定义）
├── models/                   # 自带一个 4 类苹果叶病害权重（见 models/README.md）
├── datasets/                 # 数据集定义 data.yaml（图像不随仓库分发）
├── docs/                     # 技术报告
├── assets/                   # 应用图标
├── scripts/                  # 下载预训练权重、最小推理示例
├── train.py                  # 训练脚本（YOLO 检测）
├── run_desktop.py            # 桌面端入口
├── build_exe.py              # PyInstaller 打包脚本
└── requirements.txt
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate ; Linux/macOS: source .venv/bin/activate

# 如需 GPU 推理，请按 https://pytorch.org 选择对应 CUDA 版本的 torch 安装命令
pip install -r requirements.txt
```

### 2. 启动桌面端

```bash
python run_desktop.py
```

默认账号 `admin` / `admin123`（首次启动自动创建，**请立即在界面中修改**）。账号信息只保存在 `desktop_app/.local_data/`，该目录已被 `.gitignore` 忽略。

### 3. 命令行推理

```bash
python scripts/quick_infer.py                      # 用自带权重跑数据集验证集
python scripts/quick_infer.py path/to/images       # 指定图片目录
```

### 4. 训练

```bash
# 先把数据放到 datasets/images/{train,val} 与 datasets/labels/{train,val}，类别见 datasets/data.yaml
python train.py
```

脚本默认从官方预训练权重 `yolov8n.pt` 开始微调（首次运行会自动下载），训练结果写入 `runs/train/apple_leaf_det/`。训练完成后把 `best.pt` 放到 `models/apple_leaf_best.pt`（或设置环境变量 `ALD_MODEL` 指向它）即可被桌面端使用。

### 5. 打包

```bash
python build_exe.py --model models/apple_leaf_best.pt
```

## 数据

`datasets/data.yaml` 定义了 4 个类别。训练/验证图像与标注**未包含**在本仓库中（体积与授权原因），请参考 `datasets/README.md` 自行准备 YOLO txt 格式标注。

## 模型

仓库自带的 `models/apple_leaf_best.pt` 为 YOLO 检测权重，4 类输出，见 `models/README.md`。若替换为自己的权重，注意类别数与 `datasets/data.yaml` 一致，否则会出现"框对了、类别标签错"的情况。

## 说明与限制

- 只在自制苹果叶数据集上训练过，跨品种、跨光照、跨区域的泛化能力**未验证**
- 检测结果仅作初筛参考；病斑与虫害、药害、缺素等表型可能混淆
- 可选的大模型建议由外部接口生成，可能与本地检测结果不一致，属于辅助文本
- 本项目依赖 [Ultralytics](https://github.com/ultralytics/ultralytics)（AGPL-3.0），相关预训练权重与代码遵循其原始许可

## 许可

本仓库代码以 **AGPL-3.0** 发布（见 `LICENSE`）。若需闭源商业使用，请先确认所依赖的 Ultralytics 组件与权重许可，并替换为可商用方案。

## 致谢

- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)：训练与推理管线
- [PySide6](https://www.qt.io/)：桌面界面
- DeepSeek API：可选的防治建议文本生成
