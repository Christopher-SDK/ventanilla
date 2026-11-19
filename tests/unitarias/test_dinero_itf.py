from decimal import Decimal

import pytest

from ventanilla.dominio import itf
from ventanilla.dominio.dinero import extraer_montos, extraer_porcentajes, formatear


@pytest.mark.parametrize("centimos, texto", [(0, "S/ 0,00"), (5, "S/ 0,05"), (350, "S/ 3,50"), (100000, "S/ 1 000,00"), (123456789, "S/ 1 234 567,89")])
def test_formato_peruano(centimos, texto):
    assert formatear(centimos) == texto


@pytest.mark.parametrize("texto, esperado", [
    ("cuesta S/ 3,50", [350]),
    ("cuesta S/3.50", [350]),
    ("cuesta S/. 3.50", [350]),
    ("S/ 1 000,00 o S/ 1.000,00 o S/ 1,000.00", [100000, 100000, 100000]),
    ("S/ 10 000", [1000000]),
    ("S/ 15.", [1500]),
    ("son 6,50 soles", [650]),
    ("15 días hábiles", []),
    ("el 11/12/2026", []),
])
def test_lee_montos_en_cualquier_formato(texto, esperado):
    assert extraer_montos(texto) == esperado


def test_lee_porcentajes():
    assert extraer_porcentajes("la tasa es 0,005 % y no 0.05%") == [Decimal("0.005"), Decimal("0.05")]


@pytest.mark.parametrize("monto, esperado", [
    (1_000_000, 50),   # S/ 10 000,00 -> S/ 0,50 (ejemplo del documento)
    (150_000, 5),      # S/ 1 500,00 -> 0,075 truncado a S/ 0,05
    (99_999, 0),       # menos de S/ 1 000: el impuesto truncado es cero
    (100_000, 5),
    (0, 0),
])
def test_itf_trunca_al_multiplo_de_cinco_centimos(monto, esperado):
    assert itf.calcular(monto) == esperado


def test_itf_rechaza_negativos():
    with pytest.raises(ValueError):
        itf.calcular(-1)
