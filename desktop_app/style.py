APP_STYLESHEET = """
QWidget {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 13px;
    color: #e8f5e9;
}
QMainWindow, QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0f1a12, stop:0.45 #15261a, stop:1 #1a3322);
}
QFrame#card {
    background-color: rgba(32, 52, 38, 0.92);
    border: 1px solid #2d4a35;
    border-radius: 16px;
}
QFrame#hero {
    background-color: rgba(26, 48, 32, 0.75);
    border: 1px solid #355c40;
    border-radius: 20px;
}
QLabel#title {
    font-size: 26px;
    font-weight: 700;
    color: #c8e6c9;
    letter-spacing: 1px;
}
QLabel#subtitle {
    font-size: 13px;
    color: #a5d6a7;
}
QLabel#hint {
    font-size: 12px;
    color: #81c784;
}
QLabel#section {
    font-size: 12px;
    font-weight: 700;
    color: #c5e1a5;
    letter-spacing: 0.5px;
    margin-top: 6px;
}
QFrame#sep {
    background-color: #3d5c45;
    border: none;
    max-height: 1px;
    min-height: 1px;
}
QTextEdit#aiAdvice {
    border: 1px solid #4a6b55;
    background-color: #0f1812;
    font-size: 13px;
    line-height: 1.45;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1b2e22;
    border: 1px solid #3d5c45;
    border-radius: 10px;
    padding: 10px 12px;
    color: #e8f5e9;
    selection-background-color: #558b2f;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #7cb342;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #7cb342, stop:1 #558b2f);
    color: #102010;
    font-weight: 600;
    border: none;
    border-radius: 12px;
    padding: 10px 18px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #8bc34a, stop:1 #689f38);
}
QPushButton:pressed {
    background: #33691e;
    color: #e8f5e9;
}
QPushButton#ghost {
    background: rgba(60, 90, 70, 0.55);
    color: #c8e6c9;
    border: 1px solid #4a6b55;
}
QPushButton#ghost:hover {
    background: rgba(80, 115, 90, 0.75);
}
QPushButton:disabled {
    background: #3a4a3a;
    color: #9e9e9e;
}
QProgressBar {
    border: 1px solid #3d5c45;
    border-radius: 8px;
    text-align: center;
    color: #e8f5e9;
    background-color: #142018;
    height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7cb342, stop:1 #aed581);
    border-radius: 7px;
}
QScrollArea {
    border: none;
    background: transparent;
}
QTextEdit, QPlainTextEdit {
    background-color: #121c15;
    border: 1px solid #2d4a35;
    border-radius: 10px;
    color: #dcedc8;
    padding: 8px;
}
QTabWidget::pane {
    border: 1px solid #2d4a35;
    border-radius: 12px;
    top: -1px;
    background: rgba(24, 40, 30, 0.85);
}
QTabBar::tab {
    background: #1a2a1f;
    color: #a5d6a7;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    border: 1px solid #2d4a35;
}
QTabBar::tab:selected {
    background: #2e4a32;
    color: #e8f5e9;
    font-weight: 600;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #1b2e22;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
    background: #aed581;
    border: 1px solid #33691e;
}
"""
