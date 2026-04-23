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
        SpectrometerMotor(19, 18, 21, revolution_steps=6400),
        SpectrometerOpticalPair(26),
        SpectrometerOpticalPair(27),
        motor_ratio=180,
    )
    # spectrometer = Spectrometer(grating)
    grating.motor().set_rate(10000)

    # grating.rotate_until(lambda: grating.gratings_signal().is_receiving())
    # start = grating.motor().current_steps()
    # grating.rotate_by_degrees(20)
    # grating.rotate_until(lambda: grating.gratings_signal().is_receiving())

    grating.rotate_until(lambda: grating.gratings_signal().is_receiving())
    start = grating.motor().current_steps()
    grating.rotate_by_degrees(60)
    grating.rotate_until(lambda: grating.gratings_signal().is_receiving())
    end = grating.motor().current_steps()
    print(end - start)
