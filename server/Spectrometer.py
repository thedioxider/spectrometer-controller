from math import isclose, sin, asin
from SpectrometerGrating import SpectrometerGrating
from GratingParameters import GratingParameters
from Photodiode import Photodiode
import json


class Spectrometer:
    def __init__(
        self, grating: SpectrometerGrating, photodiode: Photodiode, current_grating: int = 0, rotate_step=0.01, trust_quantity=2
    ):
        self.__grating = grating
        self.__current_grating = current_grating  # текущая решётка
        try:
            self.__load_parameters()  # пытаемся загрузить параметры, если они уже есть
            self.rotate_to_default_degree()
        except OSError:
            pass
        self.ROTATE_STEP = rotate_step  # шаг надо подбирать
        self.TRUST_QUANTITY = (
            trust_quantity  # количество точек, которое надо наблюдать, чтобы считать,
        )
        # что свет проходит (или не проходит) через щель.
        # Это на всякий случай, для защиты от ложных срабатываний
        # Если установить TRUST_QUANTITY = 1, то будет поиск до первого срабатывания
        self.__scan_from = 350
        self.__scan_to = 500

        self.__photoelement = photodiode

        # начальное положение решётки; угол, при котором угол
        # падения равен углу вторичной световой волны
        # self.reset_initial_angle()

    def __save_parameters(self):
        """Сохраняет параметры в файл"""
        with open(f"parameters{self.__current_grating}.txt", "w") as file:
            file.write(str(self.__phi0))
            file.write(str(self.__k))

    def __load_parameters(self):
        """Загружает параметры из файла; бросает исключение, если файла нет"""
        with open(f"parameters{self.__current_grating}.txt", "r") as file:
            self.__phi0 = float(file.readline())
            self.__k = float(file.readline())

    def __find_middle(self, phi1, phi2):
        """Вспомогательная функция для поиска середины светового отрезка"""
        if phi1 > phi2:
            phi2 += 360
        return ((phi1 + phi2) / 2) % 360

    def __find_first_light(self, direction=1):
        """Если дифф-решётка отцентрована, то достаточно найти только один максимум"""
        dark_counter = 0
        light_on_start = self.__photoelement.is_light()

        degree_start = self.__grating.current_degrees()

        def cond_1():
            # Начинаем с тёмной точки
            if not light_on_start:
                return True
            nonlocal dark_counter
            if self.__photoelement.is_light():
                dark_counter += 1
            else:
                dark_counter = 0
            return dark_counter == self.TRUST_QUANTITY

        self.__grating.rotate_until(cond_1, direction=direction)

        start_of_light = False
        light_counter = 0
        dark_counter = 0

        def cond_2():
            nonlocal degree_start, dark_counter, light_counter, start_of_light
            if isclose(degree_start, self.__grating.current_degrees()):
                return True
            if not self.__photoelement.is_light():
                dark_counter += 1
                light_counter = 0
            else:
                light_counter += 1
                dark_counter = 0

            if start_of_light and dark_counter == self.TRUST_QUANTITY:
                return True
            elif not start_of_light and light_counter == self.TRUST_QUANTITY:
                start_of_light = (
                    self.__grating.current_degrees() - self.TRUST_QUANTITY + 1
                )
            return False

        self.__grating.rotate_until(cond_2, direction=direction)
        if start_of_light and dark_counter == self.TRUST_QUANTITY:
            return self.__find_middle(
                start_of_light,
                self.__grating.current_degrees() - self.TRUST_QUANTITY + 1,
            )
        return None

    def __fix_default_position(self):
        current_phi = self.__grating.current_degrees()
        if not self.__photoelement.is_light():
            print("light off")
            forward_light = self.__find_first_light(direction=1)
            print("first light found")
            self.__grating.rotate_to_degrees(current_phi)
            backward_light = self.__find_first_light(direction=-1)
            print("second light found")
            if forward_light - current_phi < current_phi - backward_light:
                self.__phi0 = forward_light
            else:
                self.__phi0 = backward_light
        else:
            print("light on")
            dark_counter = 0

            def cond_1():
                nonlocal dark_counter
                if self.__photoelement.is_light():
                    dark_counter += 1
                else:
                    dark_counter = 0
                return dark_counter == self.TRUST_QUANTITY

            self.__grating.rotate_until(cond_1, direction=1)
            light_finish = self.__grating.current_degrees() - self.TRUST_QUANTITY + 1
            print("first dark found")
            self.__grating.rotate_to_degrees(current_phi)
            self.__grating.rotate_until(cond_1, direction=-1)
            print("second dark found")
            light_start = self.__grating.current_degrees() + self.TRUST_QUANTITY
            self.__phi0 = self.__find_middle(light_start, light_finish)
        self.__grating.rotate_to_degrees(self.__phi0)

    def reset_initial_angle(self):
        """Центруется по рисочке и фотоэлементу. Без включённого лазера не работает"""
        self.__grating.align_to_grating(self.__current_grating)
        print("grating aligned")
        self.__fix_default_position()
        self.__phi0 = self.__grating.current_degrees()

    def calibrate(self, lengthwave):
        """Функция калибровки спектрометра"""
        print("calibrating started")
        self.reset_initial_angle()

        maximum = self.__find_first_light()
        if maximum is None:
            print("no light found")
            return

        self.__k = lengthwave / sin(maximum - self.__phi0)
        # k - коэффициент при длине волны, равный: 2d*cos(theta), где
        # d - расстояние между щелями,
        # theta - угол падения при начальном положении решётки
        self.__save_parameters()
        self.rotate_to_default_degree()

    def rotate_to_default_degree(self):
        """Функция устанавливает спектрометр на начальное положение"""
        self.__grating.rotate_to_degrees(self.__phi0)

    def rotate_by_wavelength(self, wavelength):
        """Функция устанавливает спектрометр на заданную длину волны"""
        if wavelength < 0 or wavelength > self.__k:
            raise Exception(f"Длина волны должна быть от 0 до {self.__k}")
        self.__grating.rotate_to_degrees(self.__phi0 + asin(wavelength / self.__k))

    def get_current_wavelength(self):
        """Возвращает текущую длину волны"""
        if not self.__k:
            raise Exception("Требуется калибровка")
        return self.__k * sin(self.__grating.current_degrees() - self.__phi0)

    def __next_grating(self):
        """Меняет решётку на следующую"""
        if self.__k:
            self.__save_parameters()
        self.__current_grating = (self.__current_grating + 1) % 3
        try:
            self.__load_parameters()
        except OSError:
            self.__phi0 = (self.__phi0 + 120) % 360
            self.__k = None
        self.rotate_to_default_degree()

    def __prev_grating(self):
        """Меняет решётку на предыдущую"""
        if self.__k:
            self.__save_parameters()
        self.__current_grating = (self.__current_grating + 2) % 3
        try:
            self.__load_parameters()
        except OSError:
            self.__phi0 = (self.__phi0 + 240) % 360
            self.__k = None
        self.rotate_to_default_degree()

    def get_current_grating(self):
        """Возвращает номер текущей решётки"""
        return self.__current_grating

    def start_scan(self):
        """Выполняет сканирование с заданного угла до заданного угла
        и возвращает массив кортежей (угол, интенсивность)"""
        if not self.__k:
            raise Exception("Требуется калибровка")
        statistics = []
        self.__grating.rotate_to_degrees(self.__scan_from)

        def cond_1():
            statistics.append(
                (self.get_current_wavelength(), self.__photoelement.get_intensity())
            )
            return self.__grating.current_degrees() >= self.__scan_to

        self.__grating.rotate_until(cond_1)
        return statistics

    def get_scan_from(self):
        if not self.__k:
            raise Exception("Требуется калибровка")
        return self.__scan_from

    def set_scan_from(self, scan_from):
        if not self.__k:
            raise Exception("Требуется калибровка")
        self.__scan_from = scan_from

    def get_scan_to(self):
        if not self.__k:
            raise Exception("Требуется калибровка")
        return self.__scan_to

    def set_scan_to(self, scan_to):
        if not self.__k:
            raise Exception("Требуется калибровка")
        self.__scan_to = scan_to

    def change_grating(self, new_grating):
        """Меняет решётку на заданную"""
        if new_grating < 0 or new_grating > 2:
            raise Exception("Неверный номер решётки")
        elif (new_grating - self.__current_grating) % 3 == 1:
            self.__next_grating()
        elif (new_grating - self.__current_grating) % 3 == 2:
            self.__prev_grating()
