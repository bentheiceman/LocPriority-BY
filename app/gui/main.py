import sys
import threading

from PySide6.QtCore import QEvent, QTimer, Qt
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
from app.core.snowflake_export import (
    ACTIVATE_VIEW_SQL,
    DEFAULT_QUERY,
    SnowflakeExportError,
    activate_view,
    export_query_to_chunked_csv,
)
from app.core.theme import apply_theme
from app.core.csv_chunker import chunk_csv


# ── Status icon constants (Unicode) ─────────────────────────────────
_ICON_PENDING = "○"
_ICON_WORKING = "◌"
_ICON_OK = "●"
_ICON_FAIL = "✕"

_OBJECT_FOR_STATUS = {
    "pending": "StatusPending",
    "working": "StatusWorking",
    "ok": "StatusOk",
    "error": "StatusError",
}


def _status_icon(state: str) -> str:
    return {"pending": _ICON_PENDING, "working": _ICON_WORKING, "ok": _ICON_OK, "error": _ICON_FAIL}.get(state, "")


# ── Reusable step-card builder ──────────────────────────────────────
def _make_step_card(number: int, title: str, description: str) -> tuple[QGroupBox, QLabel]:
    """Return (group_box, status_label) for a workflow step."""
    box = QGroupBox()
    box.setObjectName("StepCard")

    outer = QVBoxLayout(box)
    outer.setSpacing(6)

    title_row = QHBoxLayout()
    title_row.setSpacing(8)
    num_label = QLabel(f"{number}")
    num_label.setObjectName("BigNum")
    num_label.setFixedWidth(36)
    num_label.setAlignment(Qt.AlignCenter)

    txt_col = QVBoxLayout()
    txt_col.setSpacing(1)
    t = QLabel(title)
    t.setObjectName("StepTitle")
    d = QLabel(description)
    d.setObjectName("StepDesc")
    d.setWordWrap(True)
    txt_col.addWidget(t)
    txt_col.addWidget(d)

    status = QLabel(f"{_ICON_PENDING}  Pending")
    status.setObjectName("StatusPending")
    status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

    title_row.addWidget(num_label, 0)
    title_row.addLayout(txt_col, 1)
    title_row.addWidget(status, 0)

    outer.addLayout(title_row)

    return box, status


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumWidth(960)
        self.setMinimumHeight(740)

        root = QWidget(self)
        root.setObjectName("CentralWidget")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 18, 20, 12)
        layout.setSpacing(10)

        # ── Header ──────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        logo = QLabel()
        logo.setFixedHeight(64)
        logo.setFixedWidth(256)
        logo.setPixmap(_svg_to_pixmap(LOGO_SVG, 256, 64))
        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        header_text_col = QVBoxLayout()
        header_text_col.setSpacing(2)

        header = QLabel("LOCPRIORITY Upload Builder")
        header.setObjectName("Header")

        sub = QLabel(f"{DEPARTMENT}  ·  Manager: {MANAGER}  ·  Developed by: {DEVELOPER}")
        sub.setObjectName("SubHeader")

        header_text_col.addWidget(header)
        header_text_col.addWidget(sub)

        header_row.addWidget(logo, 0)
        header_row.addLayout(header_text_col, 1)
        layout.addLayout(header_row)

        # ── Overall progress bar ────────────────────────────────────
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(0)
        self.overall_progress.setTextVisible(True)
        self.overall_progress.setFormat("Ready")
        self.overall_progress.setFixedHeight(24)
        layout.addWidget(self.overall_progress)

        # ── STEP 1: Authenticate ────────────────────────────────────
        self.step1_box, self.step1_status = _make_step_card(
            1, "Authenticate to Snowflake", "SSO external browser sign‑in"
        )
        s1_content = QGridLayout()
        s1_content.setHorizontalSpacing(10)
        s1_content.setVerticalSpacing(8)

        self.sf_email = QLineEdit()
        self.sf_email.setPlaceholderText("your.name@hdsupply.com")

        self.sf_insecure = QCheckBox("Use insecure_mode")
        self.sf_insecure.setChecked(True)

        self.sf_auth_btn = QPushButton("Authenticate")
        self.sf_auth_btn.clicked.connect(self._auth_snowflake)

        s1_content.addWidget(QLabel("Email"), 0, 0)
        s1_content.addWidget(self.sf_email, 0, 1)
        s1_content.addWidget(self.sf_auth_btn, 0, 2)
        s1_content.addWidget(self.sf_insecure, 1, 0, 1, 3)

        self.step1_box.layout().addLayout(s1_content)
        layout.addWidget(self.step1_box)

        # ── STEP 2: Activate Snowflake View ─────────────────────────
        self.step2_box, self.step2_status = _make_step_card(
            2,
            "Activate View (VMI classification)",
            "Deploy v_LOCPRIORITY_UPLOAD with the latest priority rules including VMI LocPriority 0",
        )
        s2_content = QHBoxLayout()
        self.activate_btn = QPushButton("Activate View in Snowflake")
        self.activate_btn.clicked.connect(self._activate_view)
        s2_content.addWidget(self.activate_btn)
        s2_content.addStretch(1)
        self.step2_box.layout().addLayout(s2_content)
        layout.addWidget(self.step2_box)

        # ── STEP 3: Generate Upload Files ───────────────────────────
        self.step3_box, self.step3_status = _make_step_card(
            3,
            "Generate Upload Files",
            "Run the export query, chunk into ≤60,000-row CSVs, and save",
        )

        s3_content = QGridLayout()
        s3_content.setHorizontalSpacing(10)
        s3_content.setVerticalSpacing(8)

        self.use_snowflake = QCheckBox("Pull data from Snowflake (recommended)")
        self.use_snowflake.setChecked(True)

        self.sf_query = QTextEdit()
        self.sf_query.setPlaceholderText("Snowflake SQL query")
        self.sf_query.setPlainText(DEFAULT_QUERY)
        self.sf_query.setMaximumHeight(90)

        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("(Alternative) Select input CSV")
        browse_in = QPushButton("Browse…")
        browse_in.setObjectName("SecondaryBtn")
        browse_in.clicked.connect(self._pick_input)

        self.output_dir = QLineEdit()
        self.output_dir.setPlaceholderText("Select output folder")
        browse_out = QPushButton("Browse…")
        browse_out.setObjectName("SecondaryBtn")
        browse_out.clicked.connect(self._pick_output_dir)

        self.base_name = QLineEdit("LOCPRIORITY_UPLOAD")
        self.base_name.setPlaceholderText("Base file name")

        self.rows_per_file = QSpinBox()
        self.rows_per_file.setRange(60000, 60000)
        self.rows_per_file.setValue(60000)
        self.rows_per_file.setEnabled(False)

        self.include_header = QCheckBox("Include header row")
        self.include_header.setChecked(True)

        self.validate_columns = QCheckBox("Validate required columns (item, loc, locpriority)")
        self.validate_columns.setChecked(True)

        row = 0
        s3_content.addWidget(self.use_snowflake, row, 0, 1, 3); row += 1
        s3_content.addWidget(QLabel("SQL"), row, 0, Qt.AlignTop)
        s3_content.addWidget(self.sf_query, row, 1, 1, 2); row += 1
        s3_content.addWidget(QLabel("Input CSV"), row, 0)
        s3_content.addWidget(self.input_path, row, 1)
        s3_content.addWidget(browse_in, row, 2); row += 1
        s3_content.addWidget(QLabel("Output folder"), row, 0)
        s3_content.addWidget(self.output_dir, row, 1)
        s3_content.addWidget(browse_out, row, 2); row += 1
        s3_content.addWidget(QLabel("Base file name"), row, 0)
        s3_content.addWidget(self.base_name, row, 1, 1, 2); row += 1
        s3_content.addWidget(self.include_header, row, 0, 1, 2)
        s3_content.addWidget(self.validate_columns, row, 2); row += 1

        self.step3_box.layout().addLayout(s3_content)

        # Generate button + step-3 progress
        gen_row = QHBoxLayout()
        self.run_btn = QPushButton("Generate upload files")
        self.run_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.run_btn.clicked.connect(self._run)

        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(0)
        self.step_progress.setTextVisible(True)
        self.step_progress.setFormat("")

        gen_row.addWidget(self.run_btn)
        gen_row.addWidget(self.step_progress, 1)
        self.step3_box.layout().addLayout(gen_row)

        layout.addWidget(self.step3_box)

        # ── Result summary cards ────────────────────────────────────
        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)

        self.stat_files = QLabel("–")
        self.stat_files.setObjectName("BigNum")
        self.stat_files.setAlignment(Qt.AlignCenter)
        self.stat_rows = QLabel("–")
        self.stat_rows.setObjectName("BigNum")
        self.stat_rows.setAlignment(Qt.AlignCenter)

        for val_lbl, name in [(self.stat_files, "Files Written"), (self.stat_rows, "Rows Written")]:
            card = QGroupBox()
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(2)
            card_layout.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(val_lbl)
            lbl = QLabel(name)
            lbl.setObjectName("BigNumLabel")
            lbl.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(lbl)
            summary_row.addWidget(card, 1)

        layout.addLayout(summary_row)

        # ── Log area ────────────────────────────────────────────────
        self.log = QTextEdit()
        self.log.setObjectName("LogBox")
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Run log will appear here…")
        layout.addWidget(self.log, 1)

        # ── Status bar ──────────────────────────────────────────────
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage(f"{DEPARTMENT}  ·  Manager: {MANAGER}  ·  Developed by: {DEVELOPER}")

        # ── Menu bar ────────────────────────────────────────────────
        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # ── Internal state ──────────────────────────────────────────
        self._auth_thread: threading.Thread | None = None
        self._authenticated = False

        # Pulse timer for indeterminate steps
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(30)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_value = 0
        self._pulse_direction = 1

    # ── Helpers ─────────────────────────────────────────────────────
    def _set_step_status(self, status_label: QLabel, state: str, text: str) -> None:
        icon = _status_icon(state)
        status_label.setText(f"{icon}  {text}")
        obj = _OBJECT_FOR_STATUS.get(state, "StatusPending")
        status_label.setObjectName(obj)
        status_label.setStyleSheet(status_label.styleSheet())  # force restyle

    def _set_overall(self, pct: int, text: str) -> None:
        self.overall_progress.setRange(0, 100)
        self.overall_progress.setValue(pct)
        self.overall_progress.setFormat(text)

    def _start_pulse(self) -> None:
        self._pulse_value = 0
        self._pulse_direction = 1
        self.step_progress.setRange(0, 100)
        self._pulse_timer.start()

    def _stop_pulse(self) -> None:
        self._pulse_timer.stop()

    def _pulse_tick(self) -> None:
        self._pulse_value += self._pulse_direction * 2
        if self._pulse_value >= 100:
            self._pulse_direction = -1
        elif self._pulse_value <= 0:
            self._pulse_direction = 1
        self.step_progress.setValue(self._pulse_value)

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

    def _post_to_ui(self, fn) -> None:
        QApplication.instance().postEvent(self, _CallableEvent(fn))

    def event(self, event):  # noqa: ANN001
        if isinstance(event, _CallableEvent):
            event.fn()
            return True
        return super().event(event)

    # ── STEP 1: Authenticate ────────────────────────────────────────
    def _auth_snowflake(self) -> None:
        email = self.sf_email.text().strip()
        insecure_mode = bool(self.sf_insecure.isChecked())

        if self._auth_thread and self._auth_thread.is_alive():
            QMessageBox.information(self, "In progress", "Authentication is already running.")
            return

        self.sf_auth_btn.setEnabled(False)
        self._set_step_status(self.step1_status, "working", "Authenticating…")
        self._set_overall(10, "Step 1/3 — Authenticating…")

        def worker() -> None:
            try:
                authenticate(email=email, insecure_mode=insecure_mode)
            except (SnowflakeAuthError, Exception) as exc:
                self._post_to_ui(lambda: self._auth_failed(str(exc)))
                return
            self._post_to_ui(self._auth_ok)

        self._auth_thread = threading.Thread(target=worker, daemon=True)
        self._auth_thread.start()

    def _auth_ok(self) -> None:
        self._authenticated = True
        self.sf_auth_btn.setEnabled(True)
        self._set_step_status(self.step1_status, "ok", "Authenticated")
        self.step1_box.setObjectName("StepDone")
        self.step1_box.setStyleSheet(self.step1_box.styleSheet())
        self._set_overall(33, "Step 1 complete — Authenticated")
        self._append_log("✓ Snowflake authentication succeeded.")
        QMessageBox.information(self, "Snowflake", "Authentication succeeded.")

    def _auth_failed(self, message: str) -> None:
        self.sf_auth_btn.setEnabled(True)
        self._set_step_status(self.step1_status, "error", "Failed")
        self._set_overall(0, "Authentication failed")
        self._append_log(f"✕ Auth failed: {message}")
        QMessageBox.warning(self, "Snowflake", message)

    # ── STEP 2: Activate View ───────────────────────────────────────
    def _activate_view(self) -> None:
        email = self.sf_email.text().strip()
        insecure_mode = bool(self.sf_insecure.isChecked())

        if not email or "@" not in email:
            QMessageBox.warning(self, "Missing email", "Enter your HD Supply email first (Step 1).")
            return

        self.activate_btn.setEnabled(False)
        self._set_step_status(self.step2_status, "working", "Deploying view…")
        self._set_overall(45, "Step 2/3 — Activating view…")

        def worker() -> None:
            try:
                activate_view(
                    email=email,
                    insecure_mode=insecure_mode,
                    on_log=lambda m: self._post_to_ui(lambda: self._append_log(m)),
                )
            except (SnowflakeExportError, Exception) as exc:
                self._post_to_ui(lambda: self._activate_failed(str(exc)))
                return
            self._post_to_ui(self._activate_ok)

        threading.Thread(target=worker, daemon=True).start()

    def _activate_ok(self) -> None:
        self.activate_btn.setEnabled(True)
        self._set_step_status(self.step2_status, "ok", "View activated")
        self.step2_box.setObjectName("StepDone")
        self.step2_box.setStyleSheet(self.step2_box.styleSheet())
        self._set_overall(55, "Step 2 complete — View activated")
        self._append_log("✓ v_LOCPRIORITY_UPLOAD view deployed successfully (VMI LocPriority 0 active).")

    def _activate_failed(self, message: str) -> None:
        self.activate_btn.setEnabled(True)
        self._set_step_status(self.step2_status, "error", "Failed")
        self._set_overall(33, "View activation failed")
        self._append_log(f"✕ Activate view failed: {message}")
        QMessageBox.warning(self, "Snowflake", f"View activation failed:\n{message}")

    # ── STEP 3: Generate ────────────────────────────────────────────
    def _run(self) -> None:
        input_csv = self.input_path.text().strip()
        output_dir = self.output_dir.text().strip()
        base_name = self.base_name.text().strip() or "LOCPRIORITY_UPLOAD"
        include_header = bool(self.include_header.isChecked())
        validate_columns = bool(self.validate_columns.isChecked())
        use_snowflake = bool(self.use_snowflake.isChecked())

        if not use_snowflake and not input_csv:
            QMessageBox.warning(self, "Missing input", "Select an input CSV, or enable Snowflake data source.")
            return
        if not output_dir:
            QMessageBox.warning(self, "Missing output", "Select an output folder.")
            return

        self.run_btn.setEnabled(False)
        self._set_step_status(self.step3_status, "working", "Running…")
        self._set_overall(70, "Step 3/3 — Generating files…")
        self._start_pulse()
        self.step_progress.setFormat("Querying & writing…")
        self.log.clear()
        self._append_log(f"Source: {'Snowflake' if use_snowflake else 'CSV'}")
        self._append_log(f"Output: {output_dir}")
        self._append_log(f"Base name: {base_name}")

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

    def _run_ok(self, result: dict, output_dir: str) -> None:
        self._stop_pulse()
        self.run_btn.setEnabled(True)
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(100)
        self.step_progress.setFormat("Complete")

        self._set_step_status(self.step3_status, "ok", "Done")
        self.step3_box.setObjectName("StepDone")
        self.step3_box.setStyleSheet(self.step3_box.styleSheet())
        self._set_overall(100, "All steps complete")

        files = result.get("files_written", 0)
        rows = result.get("rows_written", 0)
        self.stat_files.setText(str(files))
        self.stat_rows.setText(f"{rows:,}")

        self._append_log("")
        self._append_log(f"✓ Done — {files} file(s), {rows:,} row(s) written to {output_dir}")

        QMessageBox.information(
            self,
            "Complete",
            f"Generated {files} file(s) with {rows:,} rows in:\n{output_dir}",
        )

    def _run_failed(self, message: str) -> None:
        self._stop_pulse()
        self.run_btn.setEnabled(True)
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(0)
        self.step_progress.setFormat("Failed")
        self._set_step_status(self.step3_status, "error", "Failed")
        self._set_overall(55, "Generation failed")
        self._append_log(f"✕ Failed: {message}")
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
