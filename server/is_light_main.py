"""Rotate the grating motor continuously and print is_light on every step."""

from Photodiode import Photodiode
from SpectrometerMotor import SpectrometerMotor
from SpectrometerGrating import SpectrometerGrating
from SpectrometerOpticalPair import SpectrometerOpticalPair
from motor_persistence import persist_motor_state_on_exit


def main() -> None:
    grating_motor = SpectrometerMotor(
        19, 18, 21, revolution_steps=6400, rate=20000, state_file="grating_motor.json"
    )
    grating = SpectrometerGrating(
        grating_motor,
        SpectrometerOpticalPair(26),
        SpectrometerOpticalPair(27),
        motor_ratio=180,
    )
    photodiode = Photodiode(32)

    PRINT_EVERY = 1000
    step_counter = 0
    voltage_max = 0.0

    def print_and_continue():
        nonlocal step_counter, voltage_max
        step_counter += 1
        voltage = photodiode.get_voltage()
        if voltage > voltage_max:
            voltage_max = voltage
        if step_counter % PRINT_EVERY == 0:
            print(voltage_max)
            voltage_max = 0.0
        return False

    with persist_motor_state_on_exit(grating_motor):
        grating.rotate_until(print_and_continue)


if __name__ == "__main__":
    main()
