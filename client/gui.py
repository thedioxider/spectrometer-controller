"""
gui.py

PyQt6-based control interface for the ESP32 spectrometer server.
Handles network communication, scan monitoring, data plotting,
and user interaction. Thread-safe architecture with pyqtgraph visualization.
"""

import sys
import json
import time
import queue
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QLabel, QGroupBox,
    QFormLayout, QDoubleSpinBox, QSpinBox, QStatusBar,
    QDialog, QMessageBox, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
import pyqtgraph as pg


class NetworkWorker(QThread):
    """
    Background thread for HTTP communication with the ESP32 server.
    Processes commands sequentially, manages scan polling,
    and emits signals for UI updates.
    """
    response_ready = pyqtSignal(str, bool)
    scan_status_changed = pyqtSignal(str, float)
    scan_data_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.command_queue = queue.Queue()
        self.running = True
        self.scan_active = False

    def run(self) -> None:
        """Thread execution loop. Waits for commands or handles scan polling."""
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=0.5)
                if cmd is None:
                    break
                self._execute_http_command(cmd)
            except queue.Empty:
                if self.scan_active:
                    self._poll_scan_status()
                continue

    def send_command(self, cmd: str) -> None:
        """Queue a command for execution."""
        self.command_queue.put(cmd)

    def _execute_http_command(self, cmd: str) -> None:
        """Send a single command to the server and parse the response."""
        try:
            payload = {"command": cmd}
            resp = requests.post(f"{self.base_url}/api/spectrometer", json=payload, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            self.response_ready.emit(response_text, True)
            self._route_post_command(cmd, response_text)
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(f"Network error: {e}")
        except json.JSONDecodeError as e:
            self.error_occurred.emit(f"Invalid JSON response: {e}")

    def _route_post_command(self, cmd: str, response: str) -> None:
        """Trigger follow-up actions based on command type."""
        if cmd == "START-SCANS" and not self.scan_active:
            self.scan_active = True
            self.scan_status_changed.emit("running", 0.0)

        elif cmd == "?SCAN-DATA" and self.scan_active:
            try:
                parsed_data = json.loads(response) if isinstance(response, str) else response
                self.scan_data_ready.emit(parsed_data)
                self.scan_active = False
            except json.JSONDecodeError:
                self.error_occurred.emit("Failed to parse scan data.")
                self.scan_active = False

    def _poll_scan_status(self) -> None:
        """Poll server for scan progress without blocking the queue."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/spectrometer",
                json={"command": "?SCAN-STATUS"},
                timeout=2
            )
            resp.raise_for_status()
            data = resp.json()
            status_payload = data.get("response", {})
            if isinstance(status_payload, str):
                status_payload = json.loads(status_payload)

            status = status_payload.get("status", "idle")
            progress = float(status_payload.get("progress", 0.0))
            self.scan_status_changed.emit(status, progress)

            if status == "completed":
                self.send_command("?SCAN-DATA")
            elif status == "error":
                self.scan_active = False
                self.error_occurred.emit(status_payload.get("error", "Scan failed."))
        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            self.error_occurred.emit(f"Polling error: {e}")
            self.scan_active = False

    def stop(self) -> None:
        """Gracefully stop the thread."""
        self.running = False
        self.command_queue.put(None)
        self.quit()
        self.wait()


class SpectrometerGUI(QMainWindow):
    """Main application window for spectrometer control."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Spectrometer Control System")
        self.resize(1000, 780)
        self.worker = None
        self.scan_in_progress = False

        self._setup_ui()
        self._connect_signals()
        self._log("GUI initialized. Configure server IP to begin.")

    def _setup_ui(self) -> None:
        """Construct the main interface layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Connection bar
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Server URL:"))
        self.url_input = QLineEdit("http://192.168.4.1")
        conn_layout.addWidget(self.url_input)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._initialize_worker)
        conn_layout.addWidget(self.connect_btn)
        main_layout.addLayout(conn_layout)

        # Control groups
        main_layout.addWidget(self._create_navigation_group())
        main_layout.addWidget(self._create_speed_group())
        main_layout.addWidget(self._create_grating_group())
        main_layout.addWidget(self._create_scan_group())

        # Raw command & Log
        raw_layout = QHBoxLayout()
        self.raw_cmd_input = QLineEdit()
        self.raw_cmd_input.setPlaceholderText("Raw command (e.g., 532.0 GOTO)")
        self.raw_send_btn = QPushButton("Execute")
        self.raw_send_btn.clicked.connect(lambda: self._send_command(self.raw_cmd_input.text().strip()))
        raw_layout.addWidget(self.raw_cmd_input)
        raw_layout.addWidget(self.raw_send_btn)
        main_layout.addLayout(raw_layout)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("font-family: monospace; font-size: 11pt; background-color: #f8f9fa;")
        self.log_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        main_layout.addWidget(self.log_area)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Disconnected")

    def _create_navigation_group(self) -> QGroupBox:
        box = QGroupBox("Wavelength Navigation")
        layout = QFormLayout()
        self.goto_spin = QDoubleSpinBox()
        self.goto_spin.setRange(200.0, 1200.0)
        self.goto_spin.setDecimals(3)
        self.goto_spin.setValue(500.0)
        layout.addRow("Target (nm):", self.goto_spin)

        btn_layout = QHBoxLayout()
        btn_goto = QPushButton("GOTO")
        btn_goto.clicked.connect(lambda: self._send_command(f"{self.goto_spin.value():.3f} GOTO"))
        btn_read = QPushButton("?NM")
        btn_read.clicked.connect(lambda: self._send_command("?NM"))
        btn_layout.addWidget(btn_goto)
        btn_layout.addWidget(btn_read)
        layout.addRow(btn_layout)
        box.setLayout(layout)
        return box

    def _create_speed_group(self) -> QGroupBox:
        box = QGroupBox("Scan Speed")
        layout = QFormLayout()
        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(10.0, 2000.0)
        self.speed_spin.setDecimals(2)
        self.speed_spin.setValue(100.0)
        layout.addRow("Speed (nm/min):", self.speed_spin)

        btn_layout = QHBoxLayout()
        btn_set = QPushButton("Set")
        btn_set.clicked.connect(lambda: self._send_command(f"{self.speed_spin.value():.2f} NM/MIN"))
        btn_get = QPushButton("?NM/MIN")
        btn_get.clicked.connect(lambda: self._send_command("?NM/MIN"))
        btn_layout.addWidget(btn_set)
        btn_layout.addWidget(btn_get)
        layout.addRow(btn_layout)
        box.setLayout(layout)
        return box

    def _create_grating_group(self) -> QGroupBox:
        box = QGroupBox("Grating Selection")
        layout = QFormLayout()
        self.grating_spin = QSpinBox()
        self.grating_spin.setRange(1, 3)
        self.grating_spin.setValue(1)
        layout.addRow("Grating ID:", self.grating_spin)

        btn_layout = QHBoxLayout()
        btn_select = QPushButton("Select")
        btn_select.clicked.connect(lambda: self._send_command(f"{self.grating_spin.value()} GRATING"))
        btn_info = QPushButton("?GRATING")
        btn_info.clicked.connect(lambda: self._send_command("?GRATING"))
        btn_list = QPushButton("?GRATINGS")
        btn_list.clicked.connect(lambda: self._send_command("?GRATINGS"))
        btn_layout.addWidget(btn_select)
        btn_layout.addWidget(btn_info)
        btn_layout.addWidget(btn_list)
        layout.addRow(btn_layout)
        box.setLayout(layout)
        return box

    def _create_scan_group(self) -> QGroupBox:
        box = QGroupBox("Scan Configuration")
        layout = QFormLayout()

        bounds_layout = QHBoxLayout()
        self.scan_from = QDoubleSpinBox()
        self.scan_from.setRange(200.0, 1200.0)
        self.scan_from.setDecimals(2)
        self.scan_from.setValue(350.0)
        self.scan_to = QDoubleSpinBox()
        self.scan_to.setRange(200.0, 1200.0)
        self.scan_to.setDecimals(2)
        self.scan_to.setValue(500.0)
        bounds_layout.addWidget(QLabel("From:"))
        bounds_layout.addWidget(self.scan_from)
        bounds_layout.addWidget(QLabel("To:"))
        bounds_layout.addWidget(self.scan_to)
        layout.addRow(bounds_layout)

        self.scan_progress = QProgressBar()
        self.scan_progress.setValue(0)
        layout.addRow("Progress:", self.scan_progress)

        self.scan_btn = QPushButton("START-SCANS")
        self.scan_btn.clicked.connect(self._start_scan)
        layout.addRow(self.scan_btn)

        # Plot widget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel("left", "Intensity (V)")
        self.plot_widget.setLabel("bottom", "Wavelength / Position")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.scan_curve = self.plot_widget.plot(pen=pg.mkPen("b", width=2))
        layout.addRow(self.plot_widget)

        box.setLayout(layout)
        return box

    def _connect_signals(self) -> None:
        """Route worker signals to UI handlers."""
        pass  # Connected dynamically after worker initialization

    def _initialize_worker(self) -> None:
        """Create and start the network communication thread."""
        url = self.url_input.text().strip()
        if not url.startswith("http"):
            self._log("Invalid URL format.")
            return

        if self.worker and self.worker.isRunning():
            self.worker.stop()

        self.worker = NetworkWorker(url)
        self.worker.response_ready.connect(self._handle_response)
        self.worker.scan_status_changed.connect(self._update_scan_status)
        self.worker.scan_data_ready.connect(self._plot_scan_data)
        self.worker.error_occurred.connect(self._handle_error)
        self.worker.start()

        self.connect_btn.setText("Reconnect")
        self.status_bar.showMessage(f"Connected to {url}")
        self._log(f"Network worker started. Server: {url}")
        self._set_ui_state(True)

    def _send_command(self, cmd: str) -> None:
        """Send a command if the worker is active and not scanning."""
        if not self.worker or not self.worker.isRunning():
            self._log("Error: Worker not connected.")
            return
        if self.scan_in_progress and cmd not in ("?SCAN-STATUS", "?SCAN-DATA"):
            self._log("Error: System busy. Wait for scan completion.")
            return
        self._log(f"SEND: {cmd}")
        self.worker.send_command(cmd)

    def _start_scan(self) -> None:
        """Initialize and start a wavelength scan."""
        if self.scan_in_progress:
            self._log("Scan already in progress.")
            return

        self._send_command(f"{self.scan_from.value():.2f} SCAN-FROM")
        self._send_command(f"{self.scan_to.value():.2f} SCAN-TO")
        self._send_command("START-SCANS")
        self.scan_in_progress = True
        self.scan_btn.setEnabled(False)
        self.scan_progress.setValue(0)
        self.scan_curve.clear()
        self.status_bar.showMessage("Scanning in progress...")

    def _handle_response(self, text: str, success: bool) -> None:
        """Process standard command responses."""
        if success:
            try:
                parsed = json.loads(text)
                formatted = json.dumps(parsed, indent=2)
                self._log(f"RECV: {formatted}")
            except json.JSONDecodeError:
                self._log(f"RECV: {text}")
        else:
            self._log(f"RESPONSE: {text}")

    def _update_scan_status(self, status: str, progress: float) -> None:
        """Update UI elements during an active scan."""
        self.scan_progress.setValue(int(progress))
        self.status_bar.showMessage(f"Scan: {status} ({progress:.1f}%)")

    def _plot_scan_data(self, data: list) -> None:
        """Render received scan points on the plot widget."""
        if not data:
            self._log("Warning: Empty scan dataset received.")
            self._finalize_scan()
            return

        try:
            x_vals = [point[0] for point in data]
            y_vals = [point[1] for point in data]
            self.scan_curve.setData(x_vals, y_vals)
            self.plot_widget.autoRange()
            self._log(f"Scan complete. Plotted {len(data)} points.")
        except Exception as e:
            self._log(f"Plotting error: {e}")
        finally:
            self._finalize_scan()

    def _handle_error(self, message: str) -> None:
        """Display error messages and reset scan state."""
        self._log(f"ERROR: {message}")
        self._finalize_scan()

    def _finalize_scan(self) -> None:
        """Reset UI state after scan completion or failure."""
        self.scan_in_progress = False
        self.scan_btn.setEnabled(True)
        self.status_bar.showMessage("Ready.")

    def _set_ui_state(self, enabled: bool) -> None:
        """Enable/disable control groups based on connection status."""
        for group in self.findChildren(QGroupBox):
            for widget in group.findChildren(QWidget):
                if isinstance(widget, QPushButton):
                    widget.setEnabled(enabled)

    def _log(self, message: str) -> None:
        """Append timestamped message to the log area."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )

    def closeEvent(self, event) -> None:
        """Ensure clean thread termination on window close."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        event.accept()


def main() -> None:
    pg.setConfigOption("background", "w")
    pg.setConfigOption("foreground", "k")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = SpectrometerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()