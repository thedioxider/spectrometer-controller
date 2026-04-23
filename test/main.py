"""
main.py

Entry point for the spectrometer server on ESP32.
Manages Wi-Fi connection, component initialization, and server lifecycle.
"""

from Photodiode import Photodiode
import uasyncio as asyncio
import network
from Hardware_state import HardwareState
from Spectrometer import Spectrometer
from SpectrometerGrating import SpectrometerGrating
from SpectrometerMotor import SpectrometerMotor
from SpectrometerOpticalPair import SpectrometerOpticalPair
from command_parser import CommandParser
from server import start_server_async
from motor_persistence import persist_motor_state_on_exit

grating_motor = SpectrometerMotor(
    19, 18, 21, revolution_steps=6400, rate=20000, state_file="grating_motor.json"
)
grating = SpectrometerGrating(
    grating_motor,
    SpectrometerOpticalPair(26),
    SpectrometerOpticalPair(27),
    motor_ratio=180,
    calibrate_motor=True,
)
spec = Spectrometer(
    grating, Photodiode(35), current_grating=1, rotate_step=0.01, trust_quantity=3
)

with persist_motor_state_on_exit(grating_motor):
    spec.calibrate(635)
