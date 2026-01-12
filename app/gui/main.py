import sys
import threading

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSpinBox,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.brand import APP_NAME, DEPARTMENT, DEVELOPER, LOGO_SVG, MANAGER
from app.core.snowflake_auth import SnowflakeAuthError, authenticate
from app.core.snowflake_export import DEFAULT_QUERY, SnowflakeExportError, export_query_to_chunked_csv
from app.core.theme import apply_theme
from app.core.csv_chunker import chunk_csv


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(900)

        root = QWidget(self)
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header row with embedded logo + title
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        logo = QLabel()
        logo.setFixedHeight(64)
        logo.setFixedWidth(256)
        logo.setPixmap(_svg_to_pixmap(LOGO_SVG, 256, 64))
        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        header_text_col = QVBoxLayout()
        header_text_col.setSpacing(2)

        header = QLabel("Create LOCPRIORITY upload file(s) (max 60,000 rows per file)")
        header.setObjectName("Header")
        header.setWordWrap(True)

        sub = QLabel(f"{DEPARTMENT}  |  Manager: {MANAGER}  |  Developed by: {DEVELOPER}")
        sub.setObjectName("SubHeader")
        sub.setWordWrap(True)

        header_text_col.addWidget(header)
        header_text_col.addWidget(sub)

        header_row.addWidget(logo, 0)
        header_row.addLayout(header_text_col, 1)
        layout.addLayout(header_row)

        auth_box = QGroupBox("Snowflake Authentication")
        auth_layout = QGridLayout(auth_box)
        auth_layout.setHorizontalSpacing(10)
        auth_layout.setVerticalSpacing(10)

        self.sf_email = QLineEdit()
        self.sf_email.setPlaceholderText("your.name@hdsupply.com")

        self.sf_insecure = QCheckBox("Use insecure_mode (not recommended)")
        self.sf_insecure.setChecked(True)

        self.sf_auth_btn = QPushButton("Authenticate")
        self.sf_auth_btn.clicked.connect(self._auth_snowflake)

        self.sf_status = QLabel("Not authenticated")
        self.sf_status.setObjectName("SubHeader")

        auth_layout.addWidget(QLabel("Email"), 0, 0)
        auth_layout.addWidget(self.sf_email, 0, 1)
        auth_layout.addWidget(self.sf_auth_btn, 0, 2)
        auth_layout.addWidget(self.sf_insecure, 1, 0, 1, 3)
        auth_layout.addWidget(self.sf_status, 2, 0, 1, 3)

        layout.addWidget(auth_box)

        source_box = QGroupBox("Data Source")
        source_layout = QGridLayout(source_box)
        source_layout.setHorizontalSpacing(10)
        source_layout.setVerticalSpacing(10)

        self.use_snowflake = QCheckBox("Pull data from Snowflake (recommended; avoids export row limits)")
        self.use_snowflake.setChecked(True)

        self.sf_query = QTextEdit()
        self.sf_query.setPlaceholderText("Enter the SQL query to run in Snowflake")
        self.sf_query.setPlainText(DEFAULT_QUERY)

        source_layout.addWidget(self.use_snowflake, 0, 0, 1, 3)
        source_layout.addWidget(QLabel("Snowflake SQL"), 1, 0, Qt.AlignTop)
        source_layout.addWidget(self.sf_query, 1, 1, 1, 2)

        layout.addWidget(source_box)

        form = QGroupBox("Input / Output")
        form_layout = QGridLayout(form)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(10)

        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Select input CSV (export from SQL)")
        browse_in = QPushButton("Browse…")
        browse_in.clicked.connect(self._pick_input)

        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Select output folder")
        browse_out = QPushButton("Browse…")
        browse_out.clicked.connect(self._pick_output_dir)

        self.base_name = QLineEdit("LOCPRIORITY_UPLOAD")
        self.base_name.setPlaceholderText("Base file name")

        self.rows_per_file = QSpinBox()
        self.rows_per_file.setRange(60000, 60000)
        self.rows_per_file.setValue(60000)
        self.rows_per_file.setEnabled(False)

        self.include_header = QCheckBox("Include header row in each file")
        self.include_header.setChecked(True)

        self.validate_columns = QCheckBox("Validate required columns (item, loc, locpriority)")
        self.validate_columns.setChecked(True)

        form_layout.addWidget(QLabel("Input CSV"), 0, 0)
        form_layout.addWidget(self.input_path, 0, 1)
        form_layout.addWidget(browse_in, 0, 2)

        form_layout.addWidget(QLabel("Output folder"), 1, 0)
        form_layout.addWidget(self.output_dir, 1, 1)
        form_layout.addWidget(browse_out, 1, 2)

        form_layout.addWidget(QLabel("Base file name"), 2, 0)
        form_layout.addWidget(self.base_name, 2, 1, 1, 2)

        form_layout.addWidget(QLabel("Rows per file (fixed)"), 3, 0)
        form_layout.addWidget(self.rows_per_file, 3, 1)
        form_layout.addWidget(QLabel("1 file if ≤60,000 rows; 2 files if >60,000"), 3, 2)

        form_layout.addWidget(self.include_header, 4, 0, 1, 3)
        form_layout.addWidget(self.validate_columns, 5, 0, 1, 3)

        layout.addWidget(form)

        actions_row = QHBoxLayout()
        self.run_btn = QPushButton("Generate upload files")
        self.run_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.run_btn.clicked.connect(self._run)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        actions_row.addWidget(self.run_btn)
        actions_row.addWidget(self.progress, 1)
        layout.addLayout(actions_row)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Run log will appear here…")
        layout.addWidget(self.log, 1)

        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"{DEPARTMENT} • Manager: {MANAGER} • Developed by: {DEVELOPER}")

        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        self._auth_thread: threading.Thread | None = None

    def _pick_input(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select input CSV", "", "CSV Files (*.csv);;All Files (*.*)")
        if path:
            self.input_path.setText(path)

    def _pick_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select output folder")
        if path:
            self.output_dir.setText(path)

    def _append_log(self, text: str) -> None:
        self.log.append(text)

    def _set_auth_status(self, text: str) -> None:
        self.sf_status.setText(text)

    def _auth_snowflake(self) -> None:
        email = self.sf_email.text().strip()
        insecure_mode = bool(self.sf_insecure.isChecked())

        if self._auth_thread and self._auth_thread.is_alive():
            QMessageBox.information(self, "In progress", "Authentication is already running.")
            return

        self.sf_auth_btn.setEnabled(False)
        self._set_auth_status("Authenticating… (browser sign-in may open)")

        def worker() -> None:
            try:
                authenticate(email=email, insecure_mode=insecure_mode)
            except SnowflakeAuthError as exc:
                self._post_to_ui(lambda: self._auth_failed(str(exc)))
                return
            except Exception as exc:  # noqa: BLE001
                self._post_to_ui(lambda: self._auth_failed(str(exc)))
                return

            self._post_to_ui(self._auth_ok)

        self._auth_thread = threading.Thread(target=worker, daemon=True)
        self._auth_thread.start()

    def _auth_ok(self) -> None:
        self.sf_auth_btn.setEnabled(True)
        self._set_auth_status("Authenticated successfully")
        QMessageBox.information(self, "Snowflake", "Authentication succeeded.")

    def _auth_failed(self, message: str) -> None:
        self.sf_auth_btn.setEnabled(True)
        self._set_auth_status("Authentication failed")
        QMessageBox.warning(self, "Snowflake", message)

    def _post_to_ui(self, fn) -> None:
        # Queue work back onto the Qt event loop.
        QApplication.instance().postEvent(self, _CallableEvent(fn))

    def event(self, event):  # noqa: ANN001
        if isinstance(event, _CallableEvent):
            event.fn()
            return True
        return super().event(event)

    def _run(self) -> None:
        input_csv = self.input_path.text().strip()
        output_dir = self.output_dir.text().strip()
        base_name = self.base_name.text().strip() or "LOCPRIORITY_UPLOAD"
        rows_per_file = int(self.rows_per_file.value())
        include_header = bool(self.include_header.isChecked())
        validate_columns = bool(self.validate_columns.isChecked())
        use_snowflake = bool(self.use_snowflake.isChecked())

        if not use_snowflake and not input_csv:
            QMessageBox.warning(self, "Missing input", "Select an input CSV, or enable Snowflake data source.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Missing output", "Select an output folder.")
            return

        # Indeterminate while processing (no reliable total rows without a pre-scan)
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        self.log.clear()
        self._append_log(f"Input: {input_csv}")
        self._append_log(f"Output: {output_dir}")
        self._append_log(f"Base name: {base_name}")
        self._append_log(f"Source: {'Snowflake' if use_snowflake else 'CSV'}")
        self._append_log("Rows per file: 60000 (fixed)")
        def worker() -> None:
            try:
                if use_snowflake:
                    result = export_query_to_chunked_csv(
                        email=self.sf_email.text().strip(),
                        query=self.sf_query.toPlainText(),
                        output_dir=output_dir,
                        base_name=base_name,
                        max_rows=60000,
                        include_header=include_header,
                        insecure_mode=bool(self.sf_insecure.isChecked()),
                        on_log=lambda m: self._post_to_ui(lambda: self._append_log(m)),
                    )
                else:
                    result = chunk_csv(
                        input_csv=input_csv,
                        output_dir=output_dir,
                        base_name=base_name,
                        max_rows=60000,
                        include_header=include_header,
                        validate_required_columns=validate_columns,
                        on_progress=None,
                        on_log=lambda m: self._post_to_ui(lambda: self._append_log(m)),
                    )
            except (SnowflakeExportError, SnowflakeAuthError) as exc:
                self._post_to_ui(lambda: self._run_failed(str(exc)))
                return
            except Exception as exc:  # noqa: BLE001
                self._post_to_ui(lambda: self._run_failed(str(exc)))
                return

            self._post_to_ui(lambda: self._run_ok(result, output_dir))

        threading.Thread(target=worker, daemon=True).start()
        return

    def _run_ok(self, result: dict, output_dir: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self._append_log("")
        self._append_log(f"Done. Wrote {result['files_written']} file(s), {result['rows_written']} row(s).")
        QMessageBox.information(
            self,
            "Complete",
            f"Generated {result['files_written']} file(s) in:\n{output_dir}",
        )

    def _run_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        QMessageBox.critical(self, "Failed", message)


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_theme(app)

    win = MainWindow()
    win.show()
    return app.exec()


def _svg_to_pixmap(svg: str, width: int, height: int) -> QPixmap:
    renderer = QSvgRenderer(bytearray(svg, encoding="utf-8"))
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


class _CallableEvent(QEvent):
    TYPE = QEvent.Type(QEvent.registerEventType())

    def __init__(self, fn) -> None:  # noqa: ANN001
        super().__init__(self.TYPE)
        self.fn = fn
