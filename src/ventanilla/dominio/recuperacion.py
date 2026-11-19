"""Búsqueda: coseno sobre embeddings, con BM25 disponible para fusionar por rango recíproco (RRF) y como señal de abstención."""
import math
import re
from collections import Counter
from dataclasses import dataclass

from .texto import normalizar

_PALABRAS_VACIAS = set(
    "a al algo como con de del el en es esta este hay la las lo los me mi mis no o para por que se si su sus te tu tus un una y yo cual cuales cuanto cuanta "
    "cuando donde ya le les eso esa ese".split()
)


def tokens(texto: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", normalizar(texto)) if t not in _PALABRAS_VACIAS and len(t) > 1]


class Bm25:
    def __init__(self, documentos: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [Counter(tokens(d)) for d in documentos]
        self.largos = [sum(c.values()) for c in self.docs]
        self.promedio = sum(self.largos) / max(len(self.docs), 1)
        n = len(self.docs)
        df = Counter(t for c in self.docs for t in c)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def puntajes(self, consulta: str) -> list[float]:
        q = tokens(consulta)
        salida = []
        for c, largo in zip(self.docs, self.largos):
            s = 0.0
            for t in q:
                f = c.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * largo / self.promedio))
            salida.append(s)
        return salida


def coseno(a: list[float], b: list[float]) -> float:
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def rrf(rankings: list[list[int]], k: int = 60, pesos: list[float] | None = None) -> list[int]:
    """Fusión por rango recíproco (con pesos). Empates: gana el índice menor, así el orden es siempre el mismo."""
    pesos = pesos or [1.0] * len(rankings)
    puntos: dict[int, float] = {}
    for ranking, w in zip(rankings, pesos):
        for pos, idx in enumerate(ranking):
            puntos[idx] = puntos.get(idx, 0.0) + w / (k + pos + 1)
    return sorted(puntos, key=lambda i: (-puntos[i], i))


@dataclass(frozen=True)
class Hallado:
    indice: int
    bm25: float
    coseno: float


# Medido sobre evals/recuperacion.json (MRR): coseno solo 0,983 · BM25 0,25 → 0,967 · RRF 1:1 → 0,944 · BM25 solo 0,909.
# En este corpus BM25 no mejora el orden; se queda como señal de abstención. La ablación vive en tests/recuperacion.
PESO_BM25 = 0.0


def ordenar(bm25: list[float], cosenos: list[float], peso_bm25: float = PESO_BM25) -> list[Hallado]:
    por_bm25 = sorted(range(len(bm25)), key=lambda i: (-bm25[i], i))
    por_coseno = sorted(range(len(cosenos)), key=lambda i: (-cosenos[i], i))
    return [Hallado(i, bm25[i], cosenos[i]) for i in rrf([por_bm25, por_coseno], pesos=[peso_bm25, 1.0])]
