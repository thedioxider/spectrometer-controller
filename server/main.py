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

# Network credentials. Replace with actual values or load from a configuration file.
WIFI_SSID = "dobriyden"
WIFI_PASSWORD = "dendobriy"


def connect_wifi(ssid: str, password: str) -> str:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(ssid, password)
    while not wlan.isconnected():
        pass
    ip = wlan.ifconfig()[0]
    print(f"Network connected. IP address: {ip}")
    return ip


def main() -> None:
    ip = connect_wifi(WIFI_SSID, WIFI_PASSWORD)

    state = HardwareState()
    grating_motor = SpectrometerMotor(
        19, 18, 21, revolution_steps=6400, rate=10000, state_file="grating_motor.json"
    )
    grating = SpectrometerGrating(
        grating_motor,
        SpectrometerOpticalPair(26),
        SpectrometerOpticalPair(27),
        motor_ratio=180,
        calibrate_motor=True,
    )
    spec = Spectrometer(
        grating, Photodiode(32), current_grating=1, rotate_step=0.01, trust_quantity=3
    )
    parser = CommandParser(spec, state)

    with persist_motor_state_on_exit(grating_motor):
        try:
            print(f"Starting HTTP server on http://{ip}")
            asyncio.run(start_server_async(parser, port=80))
        except KeyboardInterrupt:
            print("Server interrupted")
            raise


if __name__ == "__main__":
    main()
