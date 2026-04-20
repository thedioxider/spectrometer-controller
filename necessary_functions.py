def rotate_by_degree(degree):
    """Дифракционная решётка поворачивается на заданный угол (в градусах)"""
    print(f"rotation by {degree} degree(s)")

def rotate_by_step(step=1):
    """Дифракционная решётка поворачивается на заданное количество шаагов"""
    print(f"rotation by {step} step(s)")

def is_light():
    """Возвращает True, если свет достигает точки выхода и оптопара его улавливает."""
    return True

def current_degree():
    """Возвращает текущий угол поворота дифракционной решётки от 0 до 359.(9) градусов."""
    return 0

def default_degree():
    """Устанавливает поворот на центр первой решётки, калибруясь по рисочке"""
    print("default degree")

def get_intensity():
    """Возвращает интенсивность света (уже вычисленную) с фотодиода."""
    return 0