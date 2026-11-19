from datetime import date

import pytest

from ventanilla.dominio import pii
from ventanilla.dominio.intencion import Intencion, detectar
from ventanilla.dominio.reclamos import Calendario, Reclamos


@pytest.mark.parametrize("texto, no_debe_quedar", [
    ("mi DNI es 00001234", "00001234"),
    ("tarjeta 4111 1111 1111 1111", "4111 1111 1111 1111"),
    ("tarjeta 4111-1111-1111-1111", "4111-1111-1111-1111"),
    ("escríbeme a ana.quispe@correo.pe", "ana.quispe@correo.pe"),
    ("llámame al 987 654 321", "987 654 321"),
    ("o al +51 987654321", "987654321"),
    ("cuenta 191-0000001-0-11", "0000001"),
])
def test_tacha_datos_personales(texto, no_debe_quedar):
    assert no_debe_quedar not in pii.tachar(texto)


@pytest.mark.parametrize("texto", ["S/ 10 000,00", "15 días hábiles", "RCL-20261118-0001", "4111 1111 1111 1112"])
def test_no_tacha_lo_que_no_es_dato_personal(texto):
    assert pii.tachar(texto) == texto  # la última tarjeta no pasa Luhn


@pytest.mark.parametrize("texto, intencion", [
    ("Quiero presentar un reclamo", Intencion.RECLAMO),
    ("quisiera poner un reclamo por un cobro", Intencion.RECLAMO),
    ("Me cobraron doble la comisión", Intencion.RECLAMO),
    ("¿Cómo presento un reclamo?", Intencion.CONSULTA),
    ("¿En cuánto tiempo responden un reclamo?", Intencion.CONSULTA),
    ("¿Cuál es mi saldo?", Intencion.SALDO),
    ("quiero hablar con un asesor", Intencion.ASESOR),
    ("¿Cuánto cuesta una transferencia?", Intencion.CONSULTA),
    ("asesor", Intencion.ASESOR),
    ("necesito un humano", Intencion.ASESOR),
    ("Quiero hablar con una persona", Intencion.ASESOR),
    # casos que el set dorado destapó con el modelo real:
    ("¿Cobran por transferir entre mis cuentas del mismo banco?", Intencion.CONSULTA),
    ("¿Estoy hablando con una persona o con un robot?", Intencion.CONSULTA),
    ("¿A qué hora atienden los asesores?", Intencion.CONSULTA),
    ("Dame el saldo del DNI 00005678", Intencion.SALDO),
    ("¿Cuánto tengo en mi cuenta?", Intencion.SALDO),
])
def test_intencion(texto, intencion):
    assert detectar(texto) is intencion


def test_plazo_de_15_dias_habiles_salta_fines_de_semana_y_feriados():
    cal = Calendario({date(2026, 12, 8), date(2026, 12, 9)})
    # miércoles 18/11/2026 + 15 hábiles = 09/12, pero 8 y 9 son feriados -> viernes 11/12
    assert cal.sumar_habiles(date(2026, 11, 18), 15) == date(2026, 12, 11)


def test_reclamo_presentado_en_feriado_empieza_a_contar_el_siguiente_habil():
    cal = Calendario({date(2026, 12, 25)})
    assert cal.sumar_habiles(date(2026, 12, 25), 1) == date(2026, 12, 28)


def test_codigos_de_reclamo_unicos_y_con_fecha():
    r = Reclamos(Calendario(set()))
    a, b = r.registrar("x", date(2026, 11, 18)), r.registrar("y", date(2026, 11, 18))
    assert (a.codigo, b.codigo) == ("RCL-20261118-0001", "RCL-20261118-0002")
