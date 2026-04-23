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

# Network credentials. Replace with actual values or load from a configuration file.
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"


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
    grating = SpectrometerGrating(
        SpectrometerMotor(19, 18, 21, revolution_steps=6400, rate=10000),
        SpectrometerOpticalPair(26),
        SpectrometerOpticalPair(27),
        motor_ratio=180,
    )
    spec = Spectrometer(grating, Photodiode(32), rotate_step=0.01, trust_quantity=3)
    parser = CommandParser(spec, state)

    try:
        print(f"Starting HTTP server on http://{ip}")
        asyncio.run(start_server_async(parser, port=80))
    except KeyboardInterrupt:
        print("Server interrupted")


if __name__ == "__main__":
    main()
