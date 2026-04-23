from SpectrometerMotor import SpectrometerMotor
from PolarizingFilter import PolarizingFilter
from machine import Pin, ADC
from time import sleep
PHOTODIODE_PIN = 32  # ADC input for intensity

# Hardware Init
photodiode = ADC(Pin(PHOTODIODE_PIN))
# photodiode.width(ADC.WIDTH_12BIT)
# photodiode.atten(ADC.ATTN_11DB)

led = Pin(2, Pin.OUT)
u = float(photodiode.read_uv()) / 1000000.0
print("start", u)
while True:
    u = float(photodiode.read_uv())/1000000.0
    sleep(1)
    print(u)

