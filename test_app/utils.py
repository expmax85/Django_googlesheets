import datetime
from typing import Any, Set, Iterable


def is_date(element: Any) -> bool:
    try:
        datetime.datetime.strptime(element, '%d.%m.%Y')
    except ValueError:
        return False
    return True


def is_digit(value: Any) -> bool:
    try:
        int(value)
    except TypeError:
        return False
    return True


def get_set(var: Iterable, depth_start: int = 0, depth_end: int = 4) -> Set:
    return set('~'.join(str(item) for item in elem[depth_start:depth_end]) for elem in var)
