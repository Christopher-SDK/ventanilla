"""Datos personales en texto: DNI, tarjetas, cuentas, correos y celulares (Ley 29733)."""
import re

_DNI = re.compile(r"(?<![\d-])\d{8}(?![\d-])")
_TARJETA = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_CUENTA = re.compile(r"\b(\d{3})-\d{7}-\d-(\d{2})\b")
_CORREO = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_CELULAR = re.compile(r"(?<!\d)(?:\+?51[ -]?)?9\d{2}[ -]?\d{3}[ -]?\d{3}(?!\d)")


def _luhn(digitos: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digitos)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def tachar(texto: str) -> str:
    def tarjeta(m):
        d = re.sub(r"\D", "", m.group())
        return "[tarjeta oculta]" if _luhn(d) else m.group()

    t = _TARJETA.sub(tarjeta, texto)
    t = _CUENTA.sub(lambda m: f"{m.group(1)}-*******-*-{m.group(2)}", t)
    t = _CORREO.sub("[correo oculto]", t)
    t = _CELULAR.sub("[celular oculto]", t)
    return _DNI.sub("[DNI oculto]", t)


def encontrar_dnis(texto: str) -> list[str]:
    return _DNI.findall(texto)
