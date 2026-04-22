from SpectrometerMotor import SpectrometerMotor


class PolarizingFilter:
    def __init__(self, motor: SpectrometerMotor, motor_ratio: float = 144):
        self.__motor = motor
        self._motor_ratio = motor_ratio

    def _convert_degrees_to_motor(self, degrees: float) -> float:
        return degrees * self._motor_ratio

    def motor(self):
        return self.__motor

    def current_degrees(self) -> float:
        return self.motor().current_degrees() / self._motor_ratio

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
