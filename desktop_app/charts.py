from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from desktop_app.class_names import load_class_names


def _zh_font():
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False


def save_class_bar_chart(counts: dict[int, int], out_path: Path, title: str = "各类别检测数量") -> Path:
    _zh_font()
    names = load_class_names()
    labels = []
    values = []
    for i in range(len(names)):
        labels.append(names[i].replace("Apple__", ""))
        values.append(int(counts.get(i, 0)))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=120)
    colors = ["#5c8f3c", "#7cb342", "#aed581", "#33691e", "#8bc34a", "#cddc39"][: len(labels)]
    ax.bar(labels, values, color=colors, edgecolor="#2e4a24", linewidth=0.8)
    ax.set_title(title, fontsize=14, pad=12)
    ax.set_ylabel("检测框数量")
    ax.tick_params(axis="x", rotation=18)
    for s in ax.spines.values():
        s.set_color("#3d5a2e")
    ax.set_facecolor("#f4f8f0")
    fig.patch.set_facecolor("#fafdf7")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path
