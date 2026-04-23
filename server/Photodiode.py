from machine import Pin, ADC


class Photodiode:
    def __init__(self, adc_pin, max_voltage=3.3, threshold_voltage=1):
        self._adc = ADC(Pin(adc_pin, Pin.IN))
        self._max_voltage = max_voltage
        self._threshold_voltage = threshold_voltage

    def get_voltage(self):
        raw_voltage = self._adc.read_u16()
        voltage = (raw_voltage * self._max_voltage) / 65535
        return voltage

    def get_intensity_percent(self):
        voltage = self.get_voltage()
        percent = (voltage / self._max_voltage) * 100
        return percent

    def is_light(self):
        return self.get_intensity_percent() > self._threshold_voltage
