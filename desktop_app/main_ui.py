from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QFont, QPixmap, QCloseEvent, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFileDialog,
    QDoubleSpinBox,
)

from desktop_app.auth_store import DEFAULT_PASSWORD, DEFAULT_USERNAME, verify_login
from desktop_app.charts import save_class_bar_chart
from desktop_app.deepseek_client import resolve_api_key
from desktop_app.class_names import load_class_names
from desktop_app.paths import APP_LOCAL_DIR, DEFAULT_MODEL, OUTPUT_ROOT
from desktop_app.style import APP_STYLESHEET
from desktop_app.yolo_worker import YoloWorker

SETTINGS_FILE = APP_LOCAL_DIR / "gui_settings.json"


def _load_settings() -> dict:
    APP_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.is_file():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    APP_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class DeepseekAdviceThread(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, api_key: str, stats_text: str, source_hint: str):
        super().__init__()
        self._api_key = api_key
        self._stats = stats_text
        self._hint = source_hint

    def run(self) -> None:
        from desktop_app.deepseek_client import fetch_treatment_advice

        try:
            text = fetch_treatment_advice(self._api_key, self._stats, self._hint)
            self.succeeded.emit(text)
        except Exception as e:
            self.failed.emit(str(e))


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("登录 — 苹果叶病变检测")
        self.setMinimumSize(440, 520)
        self._username = ""

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 28, 28, 28)

        hero = QFrame()
        hero.setObjectName("hero")
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(32, 36, 32, 28)

        t = QLabel("苹果叶 · 智检")
        t.setObjectName("title")
        t.setAlignment(Qt.AlignCenter)
        st = QLabel("Apple Leaf Disease Detection Studio")
        st.setObjectName("subtitle")
        st.setAlignment(Qt.AlignCenter)
        hl.addWidget(t)
        hl.addWidget(st)
        hl.addSpacing(8)

        card = QFrame()
        card.setObjectName("card")
        gl = QGridLayout(card)
        gl.setContentsMargins(22, 22, 22, 22)
        gl.setHorizontalSpacing(12)
        gl.setVerticalSpacing(14)

        gl.addWidget(QLabel("用户名"), 0, 0)
        self.ed_user = QLineEdit()
        self.ed_user.setPlaceholderText("请输入用户名")
        gl.addWidget(self.ed_user, 0, 1)

        gl.addWidget(QLabel("密码"), 1, 0)
        self.ed_pass = QLineEdit()
        self.ed_pass.setEchoMode(QLineEdit.Password)
        self.ed_pass.setPlaceholderText("请输入密码")
        gl.addWidget(self.ed_pass, 1, 1)

        btn_row = QHBoxLayout()
        btn_login = QPushButton("登 录")
        btn_login.setMinimumHeight(44)
        btn_login.clicked.connect(self._try_login)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_login)
        btn_row.addStretch(1)
        gl.addLayout(btn_row, 2, 0, 1, 2)

        hl.addWidget(card)
        hint = QLabel(
            f"首次使用默认账号：{DEFAULT_USERNAME} / {DEFAULT_PASSWORD}\n"
            f"用户数据目录：{APP_LOCAL_DIR}"
        )
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        hl.addWidget(hint)
        outer.addWidget(hero)

    def _try_login(self):
        u = self.ed_user.text().strip()
        p = self.ed_pass.text()
        ok, msg = verify_login(u, p)
        if not ok:
            QMessageBox.warning(self, "登录失败", msg)
            return
        self._username = u
        self.accept()

    def username(self) -> str:
        return self._username


class MainWindow(QMainWindow):
    def __init__(self, username: str):
        super().__init__()
        self.setWindowTitle("苹果叶病变检测工作站")
        self.resize(1180, 760)
        self._user = username
        self._last_report: dict | None = None
        self._counts_int: dict[int, int] = {}
        self._ds_thread: DeepseekAdviceThread | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(18)

        side = QFrame()
        side.setObjectName("card")
        side.setFixedWidth(322)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(18, 18, 18, 18)

        brand = QLabel("🍃 智检工作台")
        brand.setObjectName("title")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        brand.setFont(f)
        sv.addWidget(brand)
        sv.addWidget(QLabel(f"当前用户：{self._user}"))
        sv.addSpacing(6)

        sv.addWidget(QLabel("模型权重 (.pt)"))
        row_m = QHBoxLayout()
        self.ed_model = QLineEdit()
        s = _load_settings()
        self.ed_model.setText(s.get("model_path", str(DEFAULT_MODEL)))
        btn_browse_m = QPushButton("浏览…")
        btn_browse_m.setObjectName("ghost")
        btn_browse_m.clicked.connect(self._browse_model)
        row_m.addWidget(self.ed_model, 1)
        row_m.addWidget(btn_browse_m)
        sv.addLayout(row_m)
        self.btn_load = QPushButton("加载模型")
        self.btn_load.clicked.connect(self._load_model)
        sv.addWidget(self.btn_load)
        self.lbl_model_state = QLabel("模型：未加载")
        self.lbl_model_state.setObjectName("hint")
        self.lbl_model_state.setWordWrap(True)
        sv.addWidget(self.lbl_model_state)

        sv.addSpacing(10)
        sv.addWidget(QLabel("输出根目录"))
        self.lbl_out = QLabel(str(OUTPUT_ROOT))
        self.lbl_out.setObjectName("hint")
        self.lbl_out.setWordWrap(True)
        sv.addWidget(self.lbl_out)
        btn_open_out = QPushButton("打开输出文件夹")
        btn_open_out.setObjectName("ghost")
        btn_open_out.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(OUTPUT_ROOT))))
        sv.addWidget(btn_open_out)

        sep_ds = QFrame()
        sep_ds.setObjectName("sep")
        sv.addWidget(sep_ds)

        sec_ds = QLabel("DeepSeek 防治建议")
        sec_ds.setObjectName("section")
        sv.addWidget(sec_ds)

        self.ed_ds_key = QLineEdit()
        self.ed_ds_key.setEchoMode(QLineEdit.Password)
        self.ed_ds_key.setPlaceholderText("API Key（可留空，读环境变量）")
        sk = s.get("deepseek_api_key") or ""
        if sk:
            self.ed_ds_key.setText(sk)
        sv.addWidget(self.ed_ds_key)

        hint_ds = QLabel(
            f"密钥可点「保存密钥」写入：{APP_LOCAL_DIR}\n"
            "或设置系统环境变量 DEEPSEEK_API_KEY（不写盘）。"
        )
        hint_ds.setObjectName("hint")
        hint_ds.setWordWrap(True)
        sv.addWidget(hint_ds)

        row_ds = QHBoxLayout()
        btn_save_ds = QPushButton("保存密钥")
        btn_save_ds.setObjectName("ghost")
        btn_save_ds.clicked.connect(self._save_deepseek_key)
        row_ds.addWidget(btn_save_ds)
        sv.addLayout(row_ds)

        self.btn_deepseek = QPushButton("获取 AI 防治建议")
        self.btn_deepseek.clicked.connect(self._request_deepseek)
        sv.addWidget(self.btn_deepseek)

        sv.addStretch(1)
        btn_logout = QPushButton("退出登录")
        btn_logout.setObjectName("ghost")
        btn_logout.clicked.connect(self._logout)
        sv.addWidget(btn_logout)

        main = QFrame()
        main.setObjectName("card")
        mv = QVBoxLayout(main)
        mv.setContentsMargins(18, 18, 18, 18)

        tabs = QTabWidget()
        mv.addWidget(tabs, 1)

        # --- 图片页 ---
        tab_img = QWidget()
        tiv = QVBoxLayout(tab_img)
        r1 = QHBoxLayout()
        self.ed_img = QLineEdit()
        self.ed_img.setPlaceholderText("选择待检测图片…")
        b1 = QPushButton("选择图片")
        b1.setObjectName("ghost")
        b1.clicked.connect(self._browse_image)
        r1.addWidget(self.ed_img, 1)
        r1.addWidget(b1)
        tiv.addLayout(r1)
        r1b = QHBoxLayout()
        r1b.addWidget(QLabel("置信度"))
        self.sp_conf_img = QDoubleSpinBox()
        self.sp_conf_img.setRange(0.05, 0.95)
        self.sp_conf_img.setSingleStep(0.05)
        self.sp_conf_img.setValue(0.25)
        r1b.addWidget(self.sp_conf_img)
        r1b.addWidget(QLabel("输入尺寸"))
        self.sp_imgsz_img = QSpinBox()
        self.sp_imgsz_img.setRange(320, 1280)
        self.sp_imgsz_img.setSingleStep(32)
        self.sp_imgsz_img.setValue(640)
        r1b.addWidget(self.sp_imgsz_img)
        r1b.addStretch(1)
        self.btn_run_img = QPushButton("开始检测")
        self.btn_run_img.clicked.connect(self._run_image)
        r1b.addWidget(self.btn_run_img)
        tiv.addLayout(r1b)

        # --- 视频页 ---
        tab_vid = QWidget()
        tvv = QVBoxLayout(tab_vid)
        r2 = QHBoxLayout()
        self.ed_vid = QLineEdit()
        self.ed_vid.setPlaceholderText("选择待检测视频…")
        b2 = QPushButton("选择视频")
        b2.setObjectName("ghost")
        b2.clicked.connect(self._browse_video)
        r2.addWidget(self.ed_vid, 1)
        r2.addWidget(b2)
        tvv.addLayout(r2)
        r2b = QHBoxLayout()
        r2b.addWidget(QLabel("置信度"))
        self.sp_conf_vid = QDoubleSpinBox()
        self.sp_conf_vid.setRange(0.05, 0.95)
        self.sp_conf_vid.setSingleStep(0.05)
        self.sp_conf_vid.setValue(0.25)
        r2b.addWidget(self.sp_conf_vid)
        r2b.addWidget(QLabel("输入尺寸"))
        self.sp_imgsz_vid = QSpinBox()
        self.sp_imgsz_vid.setRange(320, 1280)
        self.sp_imgsz_vid.setSingleStep(32)
        self.sp_imgsz_vid.setValue(640)
        r2b.addWidget(self.sp_imgsz_vid)
        r2b.addStretch(1)
        self.btn_run_vid = QPushButton("开始检测（逐帧）")
        self.btn_run_vid.clicked.connect(self._run_video)
        r2b.addWidget(self.btn_run_vid)
        tvv.addLayout(r2b)
        self.pro_vid = QProgressBar()
        self.pro_vid.setRange(0, 100)
        self.pro_vid.setValue(0)
        tvv.addWidget(self.pro_vid)
        self.lbl_vid_status = QLabel("")
        self.lbl_vid_status.setObjectName("hint")
        tvv.addWidget(self.lbl_vid_status)

        tabs.addTab(tab_img, "图片检测")
        tabs.addTab(tab_vid, "视频检测")

        split = QSplitter(Qt.Horizontal)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        prev_wrap = QWidget()
        pv = QVBoxLayout(prev_wrap)
        pv.setContentsMargins(0, 0, 0, 0)
        self.lbl_preview = QLabel("预览与结果将显示在此区域")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumSize(520, 420)
        self.lbl_preview.setStyleSheet("background: #0f1812; border-radius: 12px; color: #81c784;")
        pv.addWidget(self.lbl_preview)
        scroll.setWidget(prev_wrap)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(130)
        lab_log = QLabel("运行日志")
        lab_log.setObjectName("section")
        rv.addWidget(lab_log)
        rv.addWidget(self.txt_log, 0)
        self.txt_stats = QTextEdit()
        self.txt_stats.setReadOnly(True)
        self.txt_stats.setMaximumHeight(160)
        lab_stats = QLabel("统计摘要")
        lab_stats.setObjectName("section")
        rv.addWidget(lab_stats)
        rv.addWidget(self.txt_stats, 0)

        lab_ai = QLabel("AI 防治建议（DeepSeek）")
        lab_ai.setObjectName("section")
        rv.addWidget(lab_ai)
        self.txt_ai_advice = QTextEdit()
        self.txt_ai_advice.setObjectName("aiAdvice")
        self.txt_ai_advice.setReadOnly(True)
        self.txt_ai_advice.setPlaceholderText(
            "完成检测后，点击左侧「获取 AI 防治建议」。需配置 API Key 或环境变量 DEEPSEEK_API_KEY。"
        )
        self.txt_ai_advice.setMinimumHeight(168)
        rv.addWidget(self.txt_ai_advice, 1)

        chart_row = QHBoxLayout()
        self.btn_bar = QPushButton("导出柱状图")
        self.btn_bar.setObjectName("ghost")
        self.btn_bar.clicked.connect(self._export_bar)
        self.btn_open_run = QPushButton("打开本次结果目录")
        self.btn_open_run.setObjectName("ghost")
        self.btn_open_run.clicked.connect(self._open_last_run)
        chart_row.addWidget(self.btn_bar)
        chart_row.addStretch(1)
        chart_row.addWidget(self.btn_open_run)
        rv.addLayout(chart_row)

        split.addWidget(scroll)
        split.addWidget(right)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)

        mv.addWidget(tabs)
        mv.addWidget(split, 1)

        root.addWidget(side)
        root.addWidget(main, 1)

        self._thread = QThread()
        self._worker = YoloWorker()
        self._worker.moveToThread(self._thread)
        self._thread.start()

        self._worker.load_done.connect(self._on_model_loaded)
        self._worker.image_done.connect(self._on_image_done)
        self._worker.video_progress.connect(self._on_video_progress)
        self._worker.video_done.connect(self._on_video_done)
        self._worker.error.connect(self._on_error)

        self._model_ready = False
        self._set_busy(False)
        self._log("界面就绪。请先加载模型权重。")
        if Path(self.ed_model.text().strip()).is_file():
            self._load_model()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._ds_thread and self._ds_thread.isRunning():
            self._ds_thread.requestInterruption()
            self._ds_thread.wait(5000)
        self._thread.quit()
        self._thread.wait(8000)
        super().closeEvent(event)

    def _log(self, text: str) -> None:
        self.txt_log.append(text)

    def _set_busy(self, busy: bool) -> None:
        self.btn_load.setEnabled(not busy)
        self.btn_run_img.setEnabled(self._model_ready and not busy)
        self.btn_run_vid.setEnabled(self._model_ready and not busy)

    def _browse_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择权重", str(DEFAULT_MODEL.parent), "PyTorch (*.pt)")
        if path:
            self.ed_model.setText(path)

    def _browse_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            str(OUTPUT_ROOT),
            "Images (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if path:
            self.ed_img.setText(path)
            pm = QPixmap(path)
            if not pm.isNull():
                self.lbl_preview.setPixmap(pm.scaled(self.lbl_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _browse_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择视频",
            str(OUTPUT_ROOT),
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv)",
        )
        if path:
            self.ed_vid.setText(path)

    def _load_model(self) -> None:
        mp = self.ed_model.text().strip()
        if not mp:
            QMessageBox.warning(self, "提示", "请先选择模型权重文件。")
            return
        _save_settings({**_load_settings(), "model_path": mp})
        self._set_busy(True)
        self.lbl_model_state.setText("模型：正在加载…")
        self._log(f"请求加载模型：{mp}")
        self._worker.request_load.emit(mp)

    def _on_model_loaded(self, ok: bool, msg: str) -> None:
        self._set_busy(False)
        if ok:
            self._model_ready = True
            self.lbl_model_state.setText("模型：已就绪")
            self._log("模型加载成功。")
        else:
            self._model_ready = False
            self.lbl_model_state.setText(f"模型：加载失败\n{msg}")
            self._log(f"模型加载失败：{msg}")
            QMessageBox.critical(self, "模型加载失败", msg)
        self.btn_run_img.setEnabled(self._model_ready)
        self.btn_run_vid.setEnabled(self._model_ready)

    def _run_image(self) -> None:
        if not self._model_ready:
            QMessageBox.warning(self, "提示", "请先成功加载模型。")
            return
        p = self.ed_img.text().strip()
        if not p or not Path(p).is_file():
            QMessageBox.warning(self, "提示", "请选择有效的图片路径。")
            return
        self._set_busy(True)
        self._log("开始图片检测…")
        self._worker.request_image.emit(p, float(self.sp_conf_img.value()), int(self.sp_imgsz_img.value()))

    def _run_video(self) -> None:
        if not self._model_ready:
            QMessageBox.warning(self, "提示", "请先成功加载模型。")
            return
        p = self.ed_vid.text().strip()
        if not p or not Path(p).is_file():
            QMessageBox.warning(self, "提示", "请选择有效的视频路径。")
            return
        self._set_busy(True)
        self.pro_vid.setValue(0)
        self.lbl_vid_status.setText("")
        self._log("开始视频检测（逐帧推理，耗时与视频长度相关）…")
        self._worker.request_video.emit(p, float(self.sp_conf_vid.value()), int(self.sp_imgsz_vid.value()))

    def _on_image_done(self, report: dict) -> None:
        self._set_busy(False)
        self._last_report = report
        self._apply_counts(report.get("counts") or {})
        self._log("图片检测完成。")
        ap = report.get("annotated_path")
        if ap and Path(ap).is_file():
            pm = QPixmap(ap)
            if not pm.isNull():
                self.lbl_preview.setPixmap(pm.scaled(self.lbl_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self._render_stats()

    def _on_video_progress(self, cur: int, total: int, hint: str) -> None:
        self.lbl_vid_status.setText(hint)
        if total > 0:
            self.pro_vid.setValue(int(min(100, cur * 100 / max(1, total))))
        else:
            self.pro_vid.setValue(min(99, cur % 100))

    def _on_video_done(self, report: dict) -> None:
        self._set_busy(False)
        self.pro_vid.setValue(100)
        self._last_report = report
        self._apply_counts(report.get("counts") or {})
        self._log("视频检测完成。输出已保存。")
        outv = report.get("output_video")
        if outv:
            self.lbl_preview.setText(f"视频已导出：\n{outv}\n\n可用系统播放器打开预览。")
            self.lbl_preview.setPixmap(QPixmap())
        self._render_stats()

    def _on_error(self, msg: str) -> None:
        self._set_busy(False)
        self._log(f"错误：{msg}")
        QMessageBox.critical(self, "运行错误", msg)

    def _apply_counts(self, counts_map: dict) -> None:
        self._counts_int = {}
        for k, v in counts_map.items():
            try:
                self._counts_int[int(k)] = int(v)
            except Exception:
                continue

    def _render_stats(self) -> None:
        names = load_class_names()
        lines = []
        total = 0
        for i, n in enumerate(names):
            c = self._counts_int.get(i, 0)
            total += c
            lines.append(f"{n}: {c}")
        lines.append(f"合计检测框: {total}")
        self.txt_stats.setPlainText("\n".join(lines))

    def _export_bar(self) -> None:
        if not self._last_report:
            QMessageBox.information(self, "提示", "请先完成一次检测。")
            return
        rd = self._last_report.get("run_dir")
        base = Path(rd) if rd else OUTPUT_ROOT
        base.mkdir(parents=True, exist_ok=True)
        out = base / "chart_bar.png"
        save_class_bar_chart(self._counts_int, out)
        self._log(f"柱状图已保存：{out}")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out)))

    def _save_deepseek_key(self) -> None:
        key = self.ed_ds_key.text().strip()
        st = {**_load_settings(), "model_path": self.ed_model.text().strip()}
        if key:
            st["deepseek_api_key"] = key
        else:
            st.pop("deepseek_api_key", None)
        _save_settings(st)
        QMessageBox.information(
            self,
            "已保存",
            f"DeepSeek 密钥已写入：{SETTINGS_FILE}\n（请勿将含密钥的配置提交到公开仓库。）\n"
            "若留空保存，将清除已存密钥并仅使用环境变量。",
        )

    def _request_deepseek(self) -> None:
        if self._ds_thread and self._ds_thread.isRunning():
            QMessageBox.information(self, "请稍候", "上一次 DeepSeek 请求尚未结束。")
            return
        key = resolve_api_key(self.ed_ds_key.text())
        if not key:
            QMessageBox.warning(
                self,
                "缺少 API Key",
                "请填写 DeepSeek API Key，或设置系统环境变量 DEEPSEEK_API_KEY 后再试。",
            )
            return
        stats = self.txt_stats.toPlainText().strip()
        if not stats:
            stats = "（当前尚无检测统计，请结合苹果叶常见病害给出一般性管理建议。）"
        if self._last_report:
            hint = (
                f"检测类型: {self._last_report.get('type', '?')}; "
                f"源文件: {self._last_report.get('source', '')}"
            )
        else:
            hint = "用户尚未在本会话中完成带统计的检测。"
        self.btn_deepseek.setEnabled(False)
        self.txt_ai_advice.setPlainText("正在请求 DeepSeek，请稍候…")
        self._log("请求 DeepSeek 防治建议…")
        self._ds_thread = DeepseekAdviceThread(key, stats, hint)
        self._ds_thread.succeeded.connect(self._on_deepseek_ok)
        self._ds_thread.failed.connect(self._on_deepseek_fail)
        self._ds_thread.finished.connect(self._on_deepseek_thread_finished)
        self._ds_thread.start()

    def _on_deepseek_ok(self, text: str) -> None:
        self.txt_ai_advice.setPlainText(text)
        self._log("DeepSeek 建议已返回。")

    def _on_deepseek_fail(self, msg: str) -> None:
        self.txt_ai_advice.clear()
        self._log(f"DeepSeek 请求失败：{msg}")
        QMessageBox.warning(self, "DeepSeek 请求失败", msg)

    def _on_deepseek_thread_finished(self) -> None:
        self.btn_deepseek.setEnabled(True)
        self._ds_thread = None

    def _open_last_run(self) -> None:
        if not self._last_report:
            QMessageBox.information(self, "提示", "暂无结果目录。")
            return
        rd = self._last_report.get("run_dir")
        if rd and Path(rd).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(rd)))

    def _logout(self) -> None:
        self.close()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        pm = self.lbl_preview.pixmap()
        if pm is not None and not pm.isNull():
            self.lbl_preview.setPixmap(pm.scaled(self.lbl_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


def run_application() -> int:
    import sys

    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)
    dlg = LoginDialog()
    if dlg.exec() != QDialog.Accepted:
        return 0
    win = MainWindow(dlg.username())
    win.show()
    win.raise_()
    win.activateWindow()
    return app.exec()
