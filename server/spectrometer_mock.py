"""
spectrometer_mock.py

Local simulation of the spectrometer hardware layer.
Implements the exact public interface required by command_parser.py.
Used exclusively for local development and protocol testing.
"""
import math
import time

class SpectrometerMock:
    def __init__(self, rotate_step=0.01, trust_quantity=2):
        self.ROTATE_STEP = rotate_step
        self.TRUST_QUANTITY = trust_quantity
        self.current_grating = 1
        self.__scan_from = 350.0
        self.__scan_to = 500.0
        self._current_nm = 500.0

    def rotate_by_wavelength(self, wavelength: float) -> None:
        self._current_nm = wavelength
        time.sleep(0.05)

    def get_current_wavelength(self) -> float:
        return self._current_nm

    def set_scan_from(self, val: float) -> None:
        self.__scan_from = val

    def set_scan_to(self, val: float) -> None:
        self.__scan_to = val

    def get_scan_from(self) -> float:
        return self.__scan_from

    def get_scan_to(self) -> float:
        return self.__scan_to

    def change_grating(self, grating_id: int) -> None:
        if 1 <= grating_id <= 3:
            self.current_grating = grating_id
            time.sleep(0.1)

    def get_current_grating(self) -> int:
        return self.current_grating

    def start_scan(self) -> list:
        points = []
        step_nm = 2.0
        current = self.__scan_from
        while current <= self.__scan_to:
            intensity = 2.5 * math.exp(-((current - 450.0) ** 2) / 1800.0) + 0.15
            intensity += (time.time() % 1 - 0.5) * 0.05
            points.append((round(current, 2), round(intensity, 3)))
            current += step_nm
            time.sleep(0.01)
        return points

    def next_grating(self) -> None:
        self.change_grating((self.current_grating % 3) + 1)