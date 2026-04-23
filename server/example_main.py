from time import sleep
from server.Photodiode import Photodiode

if __name__ == "__main__":
    diode = Photodiode(13)
    while True:
        print(diode.get_voltage())
        sleep(0.5)
