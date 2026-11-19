"""Precios desde el tarifario estructurado (la fuente del banco), no desde el modelo de lenguaje.

Visto con el modelo real: a «¿La cuenta sueldo tiene costo?» respondía «Sí, tiene costo» (es gratis).
Un monto o una condición equivocada en banca es un error con consecuencias; por eso las tarifas se buscan, no se redactan.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .dinero import formatear
from .texto import normalizar

_PIDE_PRECIO = re.compile(r"\b(cuanto|cuesta|cuestan|costo|cobran|cobra|cobro|comision|tarifa|precio|gratis|pagar|pago|how much|cost)\b")


@dataclass(frozen=True)
class Partida:
    id: str
    concepto: str
    monto_centimos: int
    condicion: str
    alias: tuple[str, ...]

    def texto(self) -> str:
        precio = "sin costo" if self.monto_centimos == 0 else formatear(self.monto_centimos)
        extra = "" if normalizar(self.condicion).rstrip(".") == precio else f" {self.condicion}"
        return f"{self.concepto}: {precio}.{extra}"


class Tarifario:
    def __init__(self, partidas: list[Partida]):
        self.partidas = partidas

    @classmethod
    def desde_archivo(cls, ruta: Path) -> "Tarifario":
        datos = json.loads(ruta.read_text(encoding="utf-8"))["partidas"]
        return cls([Partida(p["id"], p["concepto"], p["monto_centimos"], p["condicion"], tuple(normalizar(a) for a in p["alias"])) for p in datos])

    def buscar(self, pregunta: str) -> list[Partida]:
        """Las partidas que la pregunta nombra, solo si pregunta por un precio. Varias si la pregunta es general."""
        q = normalizar(pregunta)
        if not _PIDE_PRECIO.search(q) and not re.search(r"\b(tiene|hay) (costo|cobro)\b|\bes gratis\b", q):
            return []
        # Gana el alias más específico: «transferencia inmediata» le gana a «transferencia»; si la pregunta es general, salen todas.
        largo = {p.id: max((len(a) for a in p.alias if a in q), default=0) for p in self.partidas}
        mejor = max(largo.values(), default=0)
        return [p for p in self.partidas if mejor and largo[p.id] == mejor]
