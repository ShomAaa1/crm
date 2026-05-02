"""Валидаторы российских реквизитов: ИНН, КПП, ОГРН.

Используют контрольные суммы по официальным алгоритмам ФНС.
"""

import re

INN_RE = re.compile(r"^\d{10}$|^\d{12}$")
KPP_RE = re.compile(r"^\d{4}[\dA-Z]{2}\d{3}$")
OGRN_RE = re.compile(r"^\d{13}$|^\d{15}$")


def _inn_check_digit(digits: list[int], coefficients: list[int]) -> int:
    s = sum(d * c for d, c in zip(digits, coefficients, strict=False))
    return s % 11 % 10


def is_valid_inn(value: str) -> bool:
    if not value or not INN_RE.match(value):
        return False
    digits = [int(c) for c in value]

    if len(digits) == 10:
        coefs = [2, 4, 10, 3, 5, 9, 4, 6, 8]
        return _inn_check_digit(digits[:9], coefs) == digits[9]

    # 12 цифр
    coefs1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    coefs2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    return (
        _inn_check_digit(digits[:10], coefs1) == digits[10]
        and _inn_check_digit(digits[:11], coefs2) == digits[11]
    )


def is_valid_kpp(value: str) -> bool:
    if not value:
        return False
    return bool(KPP_RE.match(value))


def is_valid_ogrn(value: str) -> bool:
    if not value or not OGRN_RE.match(value):
        return False
    digits = value
    if len(digits) == 13:
        # ОГРН: контрольная цифра = (число[1..12] mod 11) mod 10
        body = int(digits[:12])
        return body % 11 % 10 == int(digits[12])
    # ОГРНИП: 15 цифр, тот же принцип, но mod 13
    body = int(digits[:14])
    return body % 13 % 10 == int(digits[14])


PASSWORD_RE = re.compile(r"^(?=.*[A-Za-zА-Яа-я])(?=.*\d).{8,}$")


def is_strong_password(value: str) -> bool:
    """Минимум 8 символов, есть буква и цифра."""
    return bool(PASSWORD_RE.match(value or ""))
