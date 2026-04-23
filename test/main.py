"""
main.py

Entry point for the spectrometer server on ESP32.
Manages Wi-Fi connection, component initialization, and server lifecycle.
"""

from server.Photodiode import Photodiode
import uasyncio as asyncio
import network
from Hardware_state import HardwareState
from Spectrometer import Spectrometer
from SpectrometerGrating import SpectrometerGrating
from SpectrometerMotor import SpectrometerMotor
from SpectrometerOpticalPair import SpectrometerOpticalPair
from command_parser import CommandParser
from server import start_server_async

grating = SpectrometerGrating(
    SpectrometerMotor(19, 18, 21, revolution_steps=6400, rate=10000),
    SpectrometerOpticalPair(26),
    SpectrometerOpticalPair(27),
    motor_ratio=180,
)
spec = Spectrometer(grating, Photodiode(32), rotate_step=0.01, trust_quantity=3)
spec.calibrate(635)