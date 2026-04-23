"""
hardware_state.py

Centralized state manager for the spectrometer system.
Tracks operational parameters, scan boundaries, grating selection,
and provides a synchronized data buffer for asynchronous scanning.
"""

import ujson as json

class HardwareState:
    def __init__(self):
        self.scan_from = 350.0
        self.scan_to = 500.0
        self.scan_speed_nm_per_min = 100.0
        self.current_grating_id = 0
        self.scan_status = "idle"  # idle, running, completed, error
        self.scan_buffer = []      # List of (degree, voltage) tuples
        self.scan_progress = 0.0
        self.error_message = None

    def set_scan_bounds(self, start_nm, stop_nm):
        if start_nm >= stop_nm:
            raise ValueError("Start wavelength must be less than stop wavelength")
        self.scan_from = float(start_nm)
        self.scan_to = float(stop_nm)

    def update_scan_status(self, status, progress=0.0):
        self.scan_status = status
        self.scan_progress = progress

    def append_scan_point(self, degree, intensity):
        self.scan_buffer.append((degree, intensity))

    def get_scan_data(self):
        return self.scan_buffer.copy()

    def clear_scan_buffer(self):
        self.scan_buffer.clear()
        self.scan_progress = 0.0
        self.error_message = None

    def set_grating(self, grating_id):
        self.current_grating_id = grating_id

    def get_status_summary(self):
        return {
            "status": self.scan_status,
            "grating": self.current_grating_id,
            "scan_from": self.scan_from,
            "scan_to": self.scan_to,
            "speed": self.scan_speed_nm_per_min,
            "progress": self.scan_progress,
            "points_collected": len(self.scan_buffer),
            "error": self.error_message
        }

    def to_json(self):
        return json.dumps(self.get_status_summary())