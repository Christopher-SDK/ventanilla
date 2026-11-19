"""Intención del mensaje con reglas fijas: lo que tiene consecuencias (reclamos, saldos, asesor) no depende del modelo."""
import re
from enum import Enum

from .texto import normalizar


class Intencion(Enum):
    ASESOR = "asesor"
    RECLAMO = "reclamo"
    SALDO = "saldo"
    CONSULTA = "consulta"


_ASESOR = re.compile(
    r"^\W*(un |una )?(asesor|asesora|humano|persona|ejecutivo)\W*$"
    r"|\b(hablar|comunicar|comunicarme|contactar|pasar|pasame|pasarme|comunicame|derivame|derivar|quiero|necesito|deseo)\b.{0,25}"
    r"\b(asesor|asesora|ejecutivo|ejecutiva|humano|persona|alguien)\b"
)
_RECLAMO = re.compile(
    r"\b(quiero|quisiera|deseo|necesito|voy a)\b.{0,25}\b(presentar|poner|hacer|registrar|ingresar|dejar)\b.{0,15}\breclamo\b"
    r"|\bquiero reclamar\b|\b(me cobraron|cobraron) (doble|dos veces|de mas|mal)\b|\bregistra(r)? (un|mi) reclamo\b"
)
_SALDO = re.compile(r"\b(mi saldo|saldo de mi|cuanto (dinero |plata )?tengo|(ver|consultar|muestrame|dame) mis cuentas|saldo de la cuenta|saldo del dni|saldo de)\b")


def detectar(texto: str) -> Intencion:
    t = normalizar(texto)
    if _RECLAMO.search(t):
        return Intencion.RECLAMO
    if _SALDO.search(t):
        return Intencion.SALDO
    if _ASESOR.search(t):
        return Intencion.ASESOR
    return Intencion.CONSULTA
