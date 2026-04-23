from machine import Pin


class SpectrometerOpticalPair:
    def __init__(self, signal_pin: int):
        self.__signal = Pin(signal_pin, Pin.IN)

    def signal(self):
        return self.__signal

    def is_receiving(self) -> bool:
        return not self.__signal.value()
