from SpectrometerOpticalPair import SpectrometerOpticalPair
from SpectrometerMotor import SpectrometerMotor
from SpectrometerGrating import SpectrometerGrating
from Photodiode import Photodiode
from Spectrometer import Spectrometer
from motor_persistence import persist_motor_state_on_exit
from time import sleep

if __name__ == "__main__":
    # diode = Photodiode(13)
    # while True:
    #     print(diode.get_voltage())
    #     sleep(0.5)
    grating_motor = SpectrometerMotor(
        19, 18, 21, revolution_steps=6400, rate=10000, state_file="grating_motor.json"
    )
    grating = SpectrometerGrating(
        grating_motor,
        SpectrometerOpticalPair(26),
        SpectrometerOpticalPair(27),
        motor_ratio=180,
    )
    photodiode = Photodiode(32)
    spectrometer = Spectrometer(grating, photodiode)

    with persist_motor_state_on_exit(grating_motor):
        grating.rotate_by_degrees(0.25)
