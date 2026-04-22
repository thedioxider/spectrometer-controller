from SpectrometerOpticalPair import SpectrometerOpticalPair
from SpectrometerMotor import SpectrometerMotor


class SpectrometerGrating:
    def __init__(
        self,
        motor: SpectrometerMotor,
        optical_pair: SpectrometerOpticalPair,
        center_offset: float = 0,
        motor_ratio: float = 10,
    ):
        self.__motor = motor
        self.__optical_pair = optical_pair
        self._center_offset = center_offset
        self._motor_ratio = motor_ratio

    def _convert_degrees_to_motor(self, degrees: float) -> float:
        return degrees * self._motor_ratio

    def motor(self) -> SpectrometerMotor:
        return self.__motor

    def optical_pair(self) -> SpectrometerOpticalPair:
        return self.__optical_pair

    def current_degrees(self) -> float:
        return self.motor().current_degrees() / self._motor_ratio

    def align_to_grating(self, grating_number: int):
        self.motor().rotate_until(lambda: self.optical_pair().is_receiving())
        self.motor().rotate_by_degrees(self._center_offset + 120 * grating_number)
        self.motor().reset_step_counter()

    def rotate_by_degrees(self, degrees: float):
        """Rotate by a certain number of degrees"""
        self.motor().rotate_by_degrees(self._convert_degrees_to_motor(degrees))

    def rotate_to_degrees(self, degrees: float):
        """Rotate to a certain position"""
        delta_1 = degrees % 360 - self.current_degrees() % 360
        delta_2 = (self.current_degrees() % 360 + 360) - degrees % 360
        if abs(delta_1) < abs(delta_2):
            self.rotate_by_degrees(delta_1)
        else:
            self.rotate_by_degrees(delta_2)

    def rotate_until(self, cond, direction=1):
        self.motor().rotate_until(cond, direction)
