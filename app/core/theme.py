from __future__ import annotations

from PySide6.QtWidgets import QApplication


THEME = {
    "bg": "#0A0A0A",
    "panel": "#111113",
    "panel2": "#161618",
    "panel3": "#1C1C1F",
    "text": "#FFD200",
    "text_alt": "#FFFFFF",
    "muted": "#C7A800",
    "muted2": "#887200",
    "border": "#2A2A2A",
    "border_glow": "#FFD20044",
    "accent": "#FFD200",
    "accent2": "#FFE15A",
    "accent_dim": "#FFD20033",
    "success": "#00C853",
    "danger": "#FF5252",
    "info": "#448AFF",
}


def apply_theme(app: QApplication) -> None:
    qss = f"""
    * {{
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 13px;
    }}

    QMainWindow {{
        background: {THEME['bg']};
        color: {THEME['text']};
    }}

    QWidget#CentralWidget {{
        background: {THEME['bg']};
    }}

    /* ── Step Cards ── */
    QGroupBox {{
        border: 1px solid {THEME['border']};
        border-radius: 12px;
        margin-top: 14px;
        padding: 16px 14px 14px 14px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                      stop:0 {THEME['panel2']}, stop:1 {THEME['panel']});
        color: {THEME['text']};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        font-size: 13px;
        font-weight: 600;
        color: {THEME['muted']};
    }}

    QGroupBox#StepActive {{
        border: 1px solid {THEME['accent']};
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                      stop:0 {THEME['panel3']}, stop:1 {THEME['panel2']});
    }}

    QGroupBox#StepDone {{
        border: 1px solid {THEME['success']};
    }}

    QGroupBox#StepDone::title {{
        color: {THEME['success']};
    }}

    /* ── Headers ── */
    QLabel#Header {{
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.5px;
        padding: 4px 0px;
        color: {THEME['text']};
    }}

    QLabel#SubHeader {{
        font-size: 11px;
        font-weight: 500;
        color: {THEME['muted']};
    }}

    QLabel#StepTitle {{
        font-size: 15px;
        font-weight: 700;
        color: {THEME['text']};
    }}

    QLabel#StepDesc {{
        font-size: 11px;
        color: {THEME['muted']};
    }}

    QLabel#StatusOk {{
        font-size: 12px;
        font-weight: 600;
        color: {THEME['success']};
    }}

    QLabel#StatusError {{
        font-size: 12px;
        font-weight: 600;
        color: {THEME['danger']};
    }}

    QLabel#StatusPending {{
        font-size: 12px;
        font-weight: 600;
        color: {THEME['muted2']};
    }}

    QLabel#StatusWorking {{
        font-size: 12px;
        font-weight: 600;
        color: {THEME['info']};
    }}

    QLabel#BigNum {{
        font-size: 28px;
        font-weight: 800;
        color: {THEME['accent']};
    }}

    QLabel#BigNumLabel {{
        font-size: 11px;
        font-weight: 600;
        color: {THEME['muted']};
    }}

    /* ── Input widgets ── */
    QLineEdit, QTextEdit, QSpinBox {{
        background: {THEME['panel']};
        border: 1px solid {THEME['border']};
        border-radius: 8px;
        padding: 8px 10px;
        color: {THEME['text_alt']};
        selection-background-color: {THEME['accent']};
        selection-color: #000000;
    }}

    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
        border: 1px solid {THEME['accent']};
    }}

    QLineEdit:disabled, QTextEdit:disabled, QSpinBox:disabled {{
        color: {THEME['muted2']};
        background: {THEME['bg']};
    }}

    /* ── Buttons ── */
    QPushButton {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                      stop:0 {THEME['accent2']}, stop:1 {THEME['accent']});
        color: #000000;
        border: 0px;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 700;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background: {THEME['accent2']};
    }}

    QPushButton:pressed {{
        background: {THEME['accent']};
        padding: 11px 20px 9px 20px;
    }}

    QPushButton:disabled {{
        background: {THEME['border']};
        color: {THEME['muted2']};
    }}

    QPushButton#SecondaryBtn {{
        background: {THEME['panel2']};
        color: {THEME['accent']};
        border: 1px solid {THEME['accent']};
    }}

    QPushButton#SecondaryBtn:hover {{
        background: {THEME['accent_dim']};
    }}

    QPushButton#DangerBtn {{
        background: {THEME['danger']};
        color: #FFFFFF;
    }}

    /* ── Checkboxes ── */
    QCheckBox {{
        spacing: 10px;
        color: {THEME['text']};
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {THEME['border']};
        background: {THEME['panel']};
    }}

    QCheckBox::indicator:checked {{
        background: {THEME['accent']};
        border: 1px solid {THEME['accent']};
    }}

    /* ── Progress Bar ── */
    QProgressBar {{
        background: {THEME['panel']};
        border: 1px solid {THEME['border']};
        border-radius: 10px;
        text-align: center;
        color: {THEME['muted']};
        height: 22px;
        font-weight: 600;
        font-size: 11px;
    }}

    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                      stop:0 {THEME['accent']}, stop:1 {THEME['accent2']});
        border-radius: 10px;
    }}

    /* ── Log ── */
    QTextEdit#LogBox {{
        background: {THEME['bg']};
        border: 1px solid {THEME['border']};
        border-radius: 10px;
        padding: 10px;
        font-family: "Cascadia Code", "Consolas", monospace;
        font-size: 12px;
        color: {THEME['muted']};
    }}

    /* ── Menu / Status ── */
    QMenuBar {{
        background: {THEME['panel']};
        color: {THEME['text']};
        border-bottom: 1px solid {THEME['border']};
        padding: 2px;
    }}

    QMenuBar::item:selected {{
        background: {THEME['border']};
        border-radius: 4px;
    }}

    QMenu {{
        background: {THEME['panel']};
        color: {THEME['text']};
        border: 1px solid {THEME['border']};
        border-radius: 8px;
        padding: 4px;
    }}

    QMenu::item {{
        padding: 6px 24px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background: {THEME['border']};
    }}

    QStatusBar {{
        background: {THEME['panel']};
        color: {THEME['muted2']};
        border-top: 1px solid {THEME['border']};
        font-size: 11px;
        padding: 2px 8px;
    }}

    /* ── Scroll Bars ── */
    QScrollBar:vertical {{
        background: {THEME['bg']};
        width: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background: {THEME['border']};
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {THEME['muted2']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """

    app.setStyleSheet(qss)
