import datetime
from typing import Any, Set, Iterable


def is_date(value: Any) -> bool:
    """
    Check the value is date or not

    :return: Bool
    """
    try:
        datetime.datetime.strptime(value, '%d.%m.%Y')
    except ValueError:
        return False
    return True


def is_digit(value: Any) -> bool:
    """
    Check the value is digit or not

    :return: Bool
    """
    try:
        int(value)
    except TypeError:
        return False
    return True


def get_set(var: Iterable, depth_start: int = 0, depth_end: int = 4) -> Set:
    """
    Create Set with strings for future processing

    :return: Set
    """
    return set('~'.join(str(item) for item in elem[depth_start:depth_end]) for elem in var)
