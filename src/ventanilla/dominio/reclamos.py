"""Reclamos: código de seguimiento y fecha límite en días hábiles (Res. SBS 4036-2022: 15 días hábiles)."""
import itertools
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

PLAZO_DIAS_HABILES = 15


@dataclass(frozen=True)
class Reclamo:
    codigo: str
    presentado: date
    fecha_limite: date
    detalle: str


class Calendario:
    def __init__(self, feriados: set[date]):
        self.feriados = feriados

    @classmethod
    def desde_archivo(cls, ruta: Path) -> "Calendario":
        return cls({date.fromisoformat(f) for f in json.loads(ruta.read_text())["fechas"]})

    def es_habil(self, dia: date) -> bool:
        return dia.weekday() < 5 and dia not in self.feriados

    def sumar_habiles(self, desde: date, dias: int) -> date:
        """El día de presentación no cuenta; se cuentan los hábiles que siguen."""
        dia, restantes = desde, dias
        while restantes:
            dia += timedelta(days=1)
            if self.es_habil(dia):
                restantes -= 1
        return dia


class Reclamos:
    # ponytail: registro en memoria; un repositorio real (tabla con secuencia) cuando haya persistencia
    def __init__(self, calendario: Calendario):
        self.calendario = calendario
        self._secuencia = itertools.count(1)
        self.registrados: list[Reclamo] = []

    def registrar(self, detalle: str, hoy: date) -> Reclamo:
        n = next(self._secuencia)
        r = Reclamo(f"RCL-{hoy:%Y%m%d}-{n:04d}", hoy, self.calendario.sumar_habiles(hoy, PLAZO_DIAS_HABILES), detalle[:500])
        self.registrados.append(r)
        return r
