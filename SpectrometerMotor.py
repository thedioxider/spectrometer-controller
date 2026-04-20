from typing import Callable
from math import ceil
from time import sleep, sleep_us
from machine import Pin


class SpectrometerMotor:
    __EN_PIN = -1
    __DIR_PIN = -1
    __PUL_PIN = -1

    def __init__(self, revolution_steps: int = 500):
        self.__EN = Pin(-1, Pin.OUT)
        self.__DIR = Pin(-1, Pin.OUT)
        self.__PUL = Pin(-1, Pin.OUT)
        # Step counter
        self._current_steps = 0
        # Number of steps needed for a full revolution
        self._revolution_steps = revolution_steps
        # Degrees in a single step
        self._step_degrees = 360 / revolution_steps
        self.set_rate(1000)

    def _make_step(self):
        # make sure to set EN and DIR before
        self.__PUL.value(1)
        sleep_us(2)
        self.__PUL.value(0)
        sleep_us(self.__rate_period)
        self._current_steps += self.__direction

    def _set_direction(self, value):
        if value > 0:
            self.__direction = 1
        else:
            self.__direction = 0

    def _enable(self):
        self.__EN.value(0)

    def _disable(self):
        self.__EN.value(1)

    def current_steps(self) -> int:
        return self._current_steps

    def current_degrees(self) -> float:
        return self._current_steps * self._step_degrees

    def degrees_to_steps(self, degrees: float) -> int:
        return ceil(degrees / self._step_degrees)

    def set_rate(self, rate: int):
        """Set speed and direction of the motor"""
        self.__rate_steps = abs(rate)
        self.__rate_period = max(int(1_000_000 / self.__rate_steps) - 2, 2)

    def rotate_by_steps(self, steps: int):
        """Rotate by a certain number of steps"""
        self._enable()
        self._set_direction(steps)
        goal_steps = self.current_steps() + steps
        while self.current_steps() != goal_steps:
            self._make_step()

    def rotate_by_degrees(self, degrees: float):
        """Rotate by a certain number of degrees"""
        self.rotate_by_steps(self.degrees_to_steps(degrees))

    def rotate_to_degrees(self, degrees: float):
        """Rotate to a certain position"""
        delta_1 = degrees % 360 - self.current_degrees() % 360
        delta_2 = (self.current_steps() % 360 + 360) - degrees % 360
        if abs(delta_1) < abs(delta_2):
            self.rotate_by_degrees(delta_1)
        else:
            self.rotate_by_degrees(delta_2)

    def rotate_until(self, cond: Callable[[], bool], direction=1):
        self._enable()
        self._set_direction(direction)
        while not cond():
            self._make_step()
