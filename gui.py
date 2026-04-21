import sys
import json
import requests
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLineEdit, QPushButton, QTextEdit,
                             QLabel, QGroupBox, QFormLayout, QDoubleSpinBox,
                             QSpinBox, QStatusBar, QDialog, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal
from datetime import datetime

class HttpWorker(QThread):
    finished = pyqtSignal(str, bool)
    def __init__(self, url: str, command: str):
        super().__init__()
        self.url = url.rstrip('/')
        self.command = command

    def run(self):
        try:
            payload = {"command": self.command}
            resp = requests.post(f"{self.url}/api/spectrometer", json=payload, timeout=10)
            resp.raise_for_status()
            self.finished.emit(resp.text.strip(), True)
        except Exception as e:
            self.finished.emit(str(e), False)

class GratingsConfigDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_gui = parent
        self.setWindowTitle("Configure Gratings")
        self.resize(520, 420)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("JSON Configuration:"))
        self.json_edit = QTextEdit()
        self.json_edit.setAcceptRichText(False)
        self.json_edit.setStyleSheet("font-family: Consolas, monospace;")
        self._load_template()
        layout.addWidget(self.json_edit)
        btn_layout = QHBoxLayout()
        btn_reset = QPushButton("Reset Template")
        btn_reset.clicked.connect(self._load_template)
        btn_send = QPushButton("Send SET-GRATINGS")
        btn_send.clicked.connect(self._send)
        btn_close = QPushButton("Cancel")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_reset)
        btn_layout.addWidget(btn_send)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _load_template(self):
        template = {"gratings": [{"id": 1, "groove_density_mm": 1200, "blaze_nm": 500},
                                  {"id": 2, "groove_density_mm": 600, "blaze_nm": 400},
                                  {"id": 3, "groove_density_mm": 300, "blaze_nm": 350}]}
        self.json_edit.setPlainText(json.dumps(template, indent=2))

    def _send(self):
        try:
            raw = self.json_edit.toPlainText().strip()
            json.loads(raw)
            self.parent_gui.send_cmd(f"SET-GRATINGS {raw}")
            self.accept()
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "JSON Error", str(e))

class SpectrometerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectrometer Control")
        self.resize(500, 850)
        self.worker = None
        self._build_ui()
        self.log("GUI initialized")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("API URL:"))
        self.url_edit = QLineEdit("http://127.0.0.1:5000")
        url_layout.addWidget(self.url_edit)
        main_layout.addLayout(url_layout)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("font-family: Consolas, monospace; background: #f4f4f4;")
        main_layout.addWidget(self.log_box)

        main_layout.addWidget(self._nav_group())
        main_layout.addWidget(self._speed_group())
        main_layout.addWidget(self._grating_group())
        main_layout.addWidget(self._scan_group())

        raw_layout = QHBoxLayout()
        self.raw_cmd = QLineEdit()
        self.raw_cmd.setPlaceholderText("Raw command")
        btn_raw = QPushButton("Send")
        btn_raw.clicked.connect(lambda: self.send_cmd(self.raw_cmd.text().strip()))
        raw_layout.addWidget(self.raw_cmd)
        raw_layout.addWidget(btn_raw)
        main_layout.addLayout(raw_layout)

        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _nav_group(self):
        g = QGroupBox("Wavelength Navigation")
        layout = QFormLayout()
        self.goto_val = QDoubleSpinBox()
        self.goto_val.setRange(0, 9999.999)
        self.goto_val.setDecimals(3)
        self.goto_val.setValue(500.0)
        layout.addRow("Target (nm):", self.goto_val)
        hb = QHBoxLayout()
        hb.addWidget(self._btn("GOTO", lambda: self.send_cmd(f"{self.goto_val.value():.3f} GOTO")))
        hb.addWidget(self._btn("?NM", lambda: self.send_cmd("?NM")))
        layout.addRow(hb)
        g.setLayout(layout)
        return g

    def _speed_group(self):
        g = QGroupBox("Scan Speed")
        layout = QFormLayout()
        self.spd_val = QDoubleSpinBox()
        self.spd_val.setRange(0.01, 9999.99)
        self.spd_val.setDecimals(2)
        self.spd_val.setValue(100.0)
        layout.addRow("Speed (nm/min):", self.spd_val)
        hb = QHBoxLayout()
        hb.addWidget(self._btn("Set Speed", lambda: self.send_cmd(f"{self.spd_val.value():.2f} NM/MIN")))
        hb.addWidget(self._btn("?NM/MIN", lambda: self.send_cmd("?NM/MIN")))
        layout.addRow(hb)
        g.setLayout(layout)
        return g

    def _grating_group(self):
        g = QGroupBox("Grating Configuration")
        layout = QFormLayout()
        self.gr_val = QSpinBox()
        self.gr_val.setRange(1, 10)
        self.gr_val.setValue(1)
        layout.addRow("Grating ID:", self.gr_val)
        hb = QHBoxLayout()
        hb.addWidget(self._btn("Select", lambda: self.send_cmd(f"{self.gr_val.value()} GRATING")))
        hb.addWidget(self._btn("?GRATING", lambda: self.send_cmd("?GRATING")))
        hb.addWidget(self._btn("?GRATINGS", lambda: self.send_cmd("?GRATINGS")))
        hb.addWidget(self._btn("Config JSON", self._open_gratings_config))
        layout.addRow(hb)
        g.setLayout(layout)
        return g

    def _scan_group(self):
        g = QGroupBox("Scan Control")
        layout = QFormLayout()
        self.from_val = QDoubleSpinBox()
        self.from_val.setRange(0, 9999.99)
        self.from_val.setDecimals(2)
        self.from_val.setValue(350.0)
        layout.addRow("SCAN-FROM (nm):", self.from_val)
        self.to_val = QDoubleSpinBox()
        self.to_val.setRange(0, 9999.99)
        self.to_val.setDecimals(2)
        self.to_val.setValue(500.0)
        layout.addRow("SCAN-TO (nm):", self.to_val)
        hb1 = QHBoxLayout()
        hb1.addWidget(self._btn("Set FROM", lambda: self.send_cmd(f"{self.from_val.value():.2f} SCAN-FROM")))
        hb1.addWidget(self._btn("Set TO", lambda: self.send_cmd(f"{self.to_val.value():.2f} SCAN-TO")))
        layout.addRow(hb1)
        btn_start = QPushButton("START-SCANS")
        btn_start.clicked.connect(lambda: self.send_cmd("START-SCANS"))
        layout.addRow(btn_start)
        g.setLayout(layout)
        return g

    def _btn(self, text, slot):
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        return btn

    def _open_gratings_config(self):
        dialog = GratingsConfigDialog(self)
        dialog.exec()

    def send_cmd(self, cmd: str):
        if not cmd:
            return
        self.log(f"SEND: {cmd}")
        if self.worker and self.worker.isRunning():
            self.log("Previous command still running")
            return
        url = self.url_edit.text().strip()
        if not url:
            self.log("Error: URL not set")
            return
        self.worker = HttpWorker(url, cmd)
        self.worker.finished.connect(self._handle_response)
        self.worker.start()
        self.status.showMessage("Sending...")

    def _handle_response(self, text: str, success: bool):
        if success:
            try:
                parsed = json.loads(text)
                formatted = json.dumps(parsed, indent=2)
                self.log(f"RECV (JSON):\n{formatted}")
            except json.JSONDecodeError:
                self.log(f"RECV: {text}")
        else:
            self.log(f"ERROR: {text}")
        self.status.showMessage("Ready")
        self.log("-" * 40)

    def log(self, msg: str):
        self.log_box.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = SpectrometerGUI()
    win.show()
    sys.exit(app.exec())