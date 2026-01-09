from __future__ import annotations

from PySide6.QtWidgets import QApplication


THEME = {
    # Requested scheme: black with yellow text + branding accents
    "bg": "#000000",
    "panel": "#0B0B0B",
    "panel2": "#111111",
    "text": "#FFD200",
    "muted": "#C7A800",
    "border": "#2A2A2A",
    "accent": "#FFD200",
    "accent2": "#FFE15A",
    "danger": "#FF5252",
}


def apply_theme(app: QApplication) -> None:
    qss = f"""
    * {{
        font-size: 13px;
    }}

    QMainWindow {{
        background: {THEME['bg']};
        color: {THEME['text']};
    }}

    QLabel#Header {{
        font-size: 18px;
        font-weight: 600;
        padding: 4px 0px;
        color: {THEME['text']};
    }}

    QLabel#SubHeader {{
        font-size: 12px;
        font-weight: 500;
        color: {THEME['muted']};
    }}

    QGroupBox {{
        border: 1px solid {THEME['border']};
        border-radius: 10px;
        margin-top: 10px;
        padding: 12px;
        background: {THEME['panel']};
        color: {THEME['text']};
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {THEME['muted']};
    }}

    QLineEdit, QTextEdit, QSpinBox {{
        background: {THEME['panel2']};
        border: 1px solid {THEME['border']};
        border-radius: 8px;
        padding: 8px;
        color: {THEME['text']};
        selection-background-color: {THEME['accent']};
    }}

    QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {{
        border: 1px solid {THEME['accent2']};
    }}

    QPushButton {{
        background: {THEME['accent']};
        color: #000000;
        border: 0px;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background: {THEME['accent2']};
    }}

    QPushButton:disabled {{
        background: {THEME['border']};
        color: {THEME['muted']};
    }}

    QCheckBox {{
        spacing: 10px;
        color: {THEME['text']};
    }}

    QProgressBar {{
        background: {THEME['panel2']};
        border: 1px solid {THEME['border']};
        border-radius: 8px;
        text-align: center;
        color: {THEME['muted']};
        height: 18px;
    }}

    QProgressBar::chunk {{
        background: {THEME['accent']};
        border-radius: 8px;
    }}

    QMenuBar {{
        background: {THEME['panel']};
        color: {THEME['text']};
        border-bottom: 1px solid {THEME['border']};
    }}

    QMenuBar::item:selected {{
        background: {THEME['border']};
    }}

    QMenu {{
        background: {THEME['panel']};
        color: {THEME['text']};
        border: 1px solid {THEME['border']};
    }}

    QMenu::item:selected {{
        background: {THEME['border']};
    }}

    QStatusBar {{
        background: {THEME['panel']};
        color: {THEME['muted']};
        border-top: 1px solid {THEME['border']};
    }}
    """

    app.setStyleSheet(qss)
