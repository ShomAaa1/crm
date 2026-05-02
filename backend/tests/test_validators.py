from app.utils.validators import (
    is_strong_password,
    is_valid_inn,
    is_valid_kpp,
    is_valid_ogrn,
)


class TestINN:
    def test_valid_10_digit(self):
        # Реальные ИНН крупных компаний
        assert is_valid_inn("7707083893")  # Сбербанк
        assert is_valid_inn("7736207543")  # Газпром (для проверки алгоритма)

    def test_valid_12_digit_individual(self):
        # Сгенерированный валидный ИНН физлица
        assert is_valid_inn("500100732259")

    def test_invalid(self):
        assert not is_valid_inn("")
        assert not is_valid_inn("1234567890")  # неверная контрольная
        assert not is_valid_inn("123")
        assert not is_valid_inn("abcdefghij")
        assert not is_valid_inn("12345678901")  # 11 цифр


class TestKPP:
    def test_valid(self):
        assert is_valid_kpp("773601001")
        assert is_valid_kpp("7736AB001")

    def test_invalid(self):
        assert not is_valid_kpp("")
        assert not is_valid_kpp("12345")
        assert not is_valid_kpp("12345678901")


class TestOGRN:
    def test_valid_13(self):
        assert is_valid_ogrn("1027700132195")  # Сбербанк

    def test_invalid(self):
        assert not is_valid_ogrn("")
        assert not is_valid_ogrn("1234567890123")
        assert not is_valid_ogrn("abc")


class TestPassword:
    def test_strong(self):
        assert is_strong_password("Admin123!")
        assert is_strong_password("Manager123")
        assert is_strong_password("password1")

    def test_weak(self):
        assert not is_strong_password("")
        assert not is_strong_password("short1")
        assert not is_strong_password("nodigitsAAA")
        assert not is_strong_password("12345678")  # only digits
