from SpectrometerOpticalPair import SpectrometerOpticalPair
from SpectrometerMotor import SpectrometerMotor
from SpectrometerGrating import SpectrometerGrating
from Photodiode import Photodiode
from Spectrometer import Spectrometer
from time import sleep

if __name__ == "__main__":
    # diode = Photodiode(13)
    # while True:
    #     print(diode.get_voltage())
    #     sleep(0.5)
    grating = SpectrometerGrating(
        SpectrometerMotor(19, 18, 21, revolution_steps=6400, rate=10000),
        SpectrometerOpticalPair(26),
        SpectrometerOpticalPair(27),
        motor_ratio=180,
    )
    # spectrometer = Spectrometer(grating)

    grating.rotate_by_degrees(10)
    grating.rotate_by_degrees(-10)
    grating.rotate_by_degrees(10)
    grating.rotate_by_degrees(-10)
