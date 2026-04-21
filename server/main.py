# main.py
import uasyncio as asyncio
from machine import Pin, ADC
from server import connect_wifi, start_server
from command_parser import CommandParser
from SpectrometerMotor import SpectrometerMotor
from SpectrometerOpticalPair import SpectrometerOpticalPair
from SpectrometerGrating import SpectrometerGrating
from Spectrometer import Spectrometer
import necessary_functions

# Network
WIFI_SSID = "dobriyden"
WIFI_PASS = "dendobriy"

# ESP32 Pins (adjust to your wiring)
MOTOR_EN, MOTOR_DIR, MOTOR_PUL = 12, 13, 14
OPTICAL_PIN = 4      # OPB960 output (digital logic)
PHOTODIODE_PIN = 36  # ADC input for intensity

# Hardware Init
optical_in = Pin(OPTICAL_PIN, Pin.IN, Pin.PULL_DOWN)
photodiode = ADC(Pin(PHOTODIODE_PIN))
photodiode.width(ADC.WIDTH_12BIT)
photodiode.atten(ADC.ATTN_11DB)

# Interface functions
def is_light():
    return optical_in.value() == 1

def get_intensity():
    return photodiode.read()

def default_degree(current_grating=0):
    motor.disable()
    motor._current_steps = 0
    motor.enable()

def rotate_by_step():
    grating.rotate_by_degrees(spec.ROTATE_STEP)

# Patch necessary_functions module (required by Spectrometer.py)
necessary_functions.is_light = is_light
necessary_functions.get_intensity = get_intensity
necessary_functions.default_degree = default_degree
necessary_functions.rotate_by_degree = lambda deg: grating.rotate_by_degrees(deg)
necessary_functions.current_degree = lambda: grating.current_degrees()
necessary_functions.rotate_by_step = rotate_by_step

# Stage: 5-phase stepper (500 steps/rev), 1:144 worm gear reduction
motor = SpectrometerMotor(en_pin=MOTOR_EN, dir_pin=MOTOR_DIR, pul_pin=MOTOR_PUL, revolution_steps=500)
optical_pair = SpectrometerOpticalPair()
optical_pair.is_receiving = is_light
grating = SpectrometerGrating(motor=motor, optical_pair=optical_pair, center_offset=60, motor_ratio=144)
spec = Spectrometer(rotate_step=0.01, trust_quantity=2)

async def main():
    connect_wifi(WIFI_SSID, WIFI_PASS)
    parser = CommandParser(spec, motor, grating)
    start_server(parser.execute)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")