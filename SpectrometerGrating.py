from SpectrometerOpticalPair import SpectrometerOpticalPair
from SpectrometerMotor import SpectrometerMotor


class SpectrometerGrating:
    def __init__(self, motor: SpectrometerMotor, optical_pair: SpectrometerOpticalPair):
        self.__motor = motor
        self.__optical_pair = optical_pair
        self._current_degree = 0

    def motor(self) -> SpectrometerMotor:
        return self.__motor

    def optical_pair(self) -> SpectrometerOpticalPair:
        return self.__optical_pair

    def current_degree(self) -> int:
        return self._current_degree

    def align(self):
        self.motor().rotate_until(lambda: self.optical_pair().is_receiving())
