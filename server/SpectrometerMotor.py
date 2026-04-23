from math import ceil
from time import sleep, sleep_us
from machine import Pin
import ujson as json


class SpectrometerMotor:
    def __init__(
        self,
        en_pin,
        dir_pin,
        pul_pin,
        revolution_steps: int = 6400,
        rate: int = 1000,
        state_file: str = None,
    ):
        self.__EN = Pin(en_pin, Pin.OUT)
        self.__DIR = Pin(dir_pin, Pin.OUT)
        self.__PUL = Pin(pul_pin, Pin.OUT)
        # Step counter
        self._current_steps = 0
        # Number of steps needed for a full revolution
        self._revolution_steps = revolution_steps
        # Degrees in a single step
        self._step_degrees = 360 / revolution_steps
        self.set_rate(rate)
        self.__guide = None
        self.__last_guided = self._current_steps
        self.__state_file = state_file
        if state_file is not None:
            try:
                self.load_state()
            except OSError:
                pass

    def save_state(self):
        """Persist current runtime state to state_file. No-op if no file configured."""
        if self.__state_file is None:
            return
        payload = {
            "current_steps": self._current_steps,
            "revolution_steps": self._revolution_steps,
            "last_guided": self.__last_guided,
            "rate_steps": self.__rate_steps,
            "step_value": self.__step_value,
        }
        with open(self.__state_file, "w") as file:
            file.write(json.dumps(payload))

    def load_state(self):
        """Load state from state_file; raises OSError if file is missing."""
        if self.__state_file is None:
            return
        with open(self.__state_file, "r") as file:
            payload = json.loads(file.read())
        # A change in revolution_steps invalidates the saved step counter.
        if payload.get("revolution_steps") != self._revolution_steps:
            return
        self._current_steps = int(payload["current_steps"])
        self.__last_guided = int(payload["last_guided"])

    def _make_step(self):
        # make sure to set EN and DIR before
        self.__PUL.value(1)
        sleep_us(2)
        self.__PUL.value(0)
        sleep_us(self.__rate_period)
        if self.__direction:
            self._current_steps += self.__step_value
        else:
            self._current_steps -= self.__step_value

    def _set_direction(self, value):
        if value * self.__step_value > 0:
            self.__direction = 1
        else:
            self.__direction = 0
        self.__DIR.value(self.__direction)

    def _fetch_guide(self):
        if (
            abs(self.current_steps() - self.__last_guided)
            < self._revolution_steps / 100
        ):
            return

        if self.__guide is not None and self.__guide():
            revolutions = self.current_steps() / self._revolution_steps
            full_revolutions = round(revolutions)
            self._current_steps = full_revolutions * self._revolution_steps
            self.__last_guided = self.current_steps()

    def set_guide(self, guide):
        self.__guide = guide
        self.rotate_until(guide)
        self.reset_step_counter()

    def reset_step_counter(self):
        self._current_steps = 0

    def enable(self):
        self.__EN.value(0)

    def disable(self):
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
        self.__step_value = (rate > 0) - (rate < 0)

    def rotate_by_steps(self, steps: int):
        """Rotate by a certain number of steps"""
        self.enable()
        self._set_direction(steps)
        goal_steps = self.current_steps() + steps
        while self.current_steps() != goal_steps:
            self._make_step()
            self._fetch_guide()

    def rotate_by_degrees(self, degrees: float):
        """Rotate by a certain number of degrees"""
        self.rotate_by_steps(self.degrees_to_steps(degrees))

    def rotate_to_degrees(self, degrees: float):
        """Rotate to a certain position"""
        delta_1 = degrees % 360 - self.current_degrees() % 360
        delta_2 = (self.current_degrees() % 360 + 360) - degrees % 360
        if abs(delta_1) < abs(delta_2):
            self.rotate_by_degrees(delta_1)
        else:
            self.rotate_by_degrees(delta_2)

    def rotate_until(self, cond, direction=1):
        self.enable()
        self._set_direction(direction)
        while not cond():
            self._make_step()
            self._fetch_guide()
