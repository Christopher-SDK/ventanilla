"""Montos en céntimos (int) y su lectura desde texto libre."""
import re
from decimal import Decimal

_ENTERO = r"(\d{1,3}(?:[ .,  ]\d{3})+|\d+)"
_DECIMAL = r"(?:[.,](\d{1,2}))?(?![\d])"
_CON_SIMBOLO = re.compile(r"S/\.?\s*" + _ENTERO + _DECIMAL)
_CON_PALABRA = re.compile(r"(?<![\d/.,])" + _ENTERO + _DECIMAL + r"\s*(?:soles|nuevos soles)\b", re.IGNORECASE)
_PORCENTAJE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


def formatear(centimos: int) -> str:
    """1234550 -> 'S/ 12 345,50' (formato peruano, como en Cuadre)."""
    signo = "-" if centimos < 0 else ""
    soles, cent = divmod(abs(centimos), 100)
    miles = f"{soles:,}".replace(",", " ")
    return f"{signo}S/ {miles},{cent:02d}"


def _a_centimos(entero: str, decimales: str | None) -> int:
    soles = int(re.sub(r"\D", "", entero))
    cent = int((decimales or "0").ljust(2, "0"))
    return soles * 100 + cent


def extraer_montos(texto: str) -> list[int]:
    """Todos los montos en soles que aparecen en el texto, en céntimos."""
    vistos = []
    for patron in (_CON_SIMBOLO, _CON_PALABRA):
        for m in patron.finditer(texto):
            vistos.append((m.start(), _a_centimos(m.group(1), m.group(2))))
    return [c for _, c in sorted(vistos)]


def extraer_porcentajes(texto: str) -> list[Decimal]:
    return [Decimal(p.replace(",", ".")).normalize() for p in _PORCENTAJE.findall(texto)]
