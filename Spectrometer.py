from math import sin, asin
from necessary_functions import (
    is_light,
    rotate_by_degree,
    current_degree,
    default_degree,
    rotate_by_step,
    get_intensity,
)


class Spectrometer:
    def __init__(self, rotate_step=0.01, trust_quantity=2):
        try:
            self.__load_parameters()  #пытаемся загрузить параметры, если они уже есть
        except FileNotFoundError:
            pass
        self.current_grating = 0  # текущая решётка
        self.ROTATE_STEP = rotate_step  # шаг надо подбирать
        self.TRUST_QUANTITY = (
            trust_quantity  # количество точек, которое надо наблюдать, чтобы считать,
        )
        # что свет проходит (или не проходит) через щель.
        # Это на всякий случай, для защиты от ложных срабатываний
        # Если установить TRUST_QUANTITY = 1, то будет поиск до первого срабатывания
        self.__scan_from = 350
        self.__scan_to = 500

        # начальное положение решётки; угол, при котором угол
        # падения равен углу вторичной световой волны
        self.reset_initial_angle()

    def __find_middle(self, phi1, phi2):
        """Вспомогательная функция для поиска середины светового отрезка"""
        if phi1 > phi2:
            phi2 += 360
        return ((phi1 + phi2) / 2) % 360

    def __find_first_light(self):
        """Если дифф-решётка отцентрована, то достаточно найти только один максимум"""
        dark_counter = 0
        light_on_start = is_light()

        degree_start = current_degree()

        # Начинаем с тёмной точки
        while light_on_start:
            rotate_by_degree(self.ROTATE_STEP)
            if is_light():
                dark_counter += 1
            else:
                dark_counter = 0
            if dark_counter == self.TRUST_QUANTITY:
                break
        start_of_light = False
        light_counter = 0
        dark_counter = 0

        while degree_start != current_degree():
            if not is_light():
                dark_counter += 1
                light_counter = 0
            else:
                light_counter += 1
                dark_counter = 0

            if start_of_light and dark_counter == self.TRUST_QUANTITY:
                return self.__find_middle(
                    start_of_light, current_degree() - self.TRUST_QUANTITY + 1
                )
            elif not start_of_light and light_counter == self.TRUST_QUANTITY:
                start_of_light = current_degree() - self.TRUST_QUANTITY + 1

            rotate_by_degree(self.ROTATE_STEP)
        return None

    def reset_initial_angle(self):
        default_degree()
        if self.current_grating>0:
            rotate_by_degree(120*self.current_grating)
        self.__phi0 = current_degree()

    def calibrate(self, lengthwave):
        """Функция калибровки спектрометра"""
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
        rotate_by_degree(self.__phi0 - current_degree())

    def rotate_by_wavelength(self, wavelength):
        """Функция устанавливает спектрометр на заданную длину волны"""
        if wavelength < 0 or wavelength > self.__k:
            raise Exception(f"Длина волны должна быть от 0 до {self.__k}")
        rotate_by_degree(self.__phi0 - current_degree() + asin(wavelength / self.__k))

    def get_current_wavelength(self):
        """Возвращает текущую длину волны"""
        if not self.__k:
            raise Exception("Требуется калибровка")
        return self.__k * sin(current_degree() - self.__phi0)

    def next_grating(self):
        """Меняет решётку на следующую"""
        if self.__k:
            self.__save_parameters()
        self.current_grating = (self.current_grating + 1) % 3
        try:
            self.__load_parameters()
        except FileNotFoundError:
            self.__phi0 = (self.__phi0 + 120) % 360
            self.__k = None
        self.rotate_to_default_degree()

    def prev_grating(self):
        """Меняет решётку на предыдущую"""
        if self.__k:
            self.__save_parameters()
        self.current_grating = (self.current_grating + 2) % 3
        try:
            self.__load_parameters()
        except FileNotFoundError:
            self.__phi0 = (self.__phi0 + 240) % 360
            self.__k = None
        self.rotate_to_default_degree()


    def get_current_grating(self):
        """Возвращает номер текущей решётки"""
        return self.current_grating

    def start_scan(self):
        """Выполняет сканирование с заданного угла до заданного угла
        и возвращает массив кортежей (угол, интенсивность)"""
        if not self.__k:
            raise Exception("Требуется калибровка")
        statistics = []
        rotate_by_degree(self.__scan_from - current_degree())
        while current_degree() < self.__scan_to:
            rotate_by_step()
            statistics.append((self.get_current_wavelength(), get_intensity()))
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

    def __save_parameters(self):
        """Сохраняет параметры в файл"""
        with(open(f"parameters{self.current_grating}.txt"), "w") as file:
            file.write(self.__phi0)
            file.write(self.__k)

    def __load_parameters(self):
        """Загружает параметры из файла; бросает исключение, если файла нет"""
        with(open(f"parameters{self.current_grating}.txt"), "r") as file:
            self.__phi0 = float(file.readline())
            self.__k = float(file.readline())