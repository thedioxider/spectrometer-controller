from machine import Pin, ADC


class Photodiode:
    def __init__(
        self, adc_pin, max_voltage=3.3, threshold_voltage=0.4, koefficient=1.42
    ):
        self._adc = ADC(Pin(adc_pin, Pin.IN))
        self._max_voltage = max_voltage
        self._threshold_voltage = threshold_voltage
        self._koefficient = koefficient

    def get_voltage(self):
        voltage = self._adc.read_uv() / 10000000
        return voltage

    def get_intensity_percent(self):
        voltage = self.get_voltage()
        percent = (voltage / self._max_voltage) * 100
        return percent

    def get_intensity(self):
        return self.get_voltage() / self._koefficient

    def is_light(self):
        return self.get_voltage() > self._threshold_voltage
