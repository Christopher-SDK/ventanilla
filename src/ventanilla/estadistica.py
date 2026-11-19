"""Intervalos para tasas de acierto: con pocos casos, un 25/26 no es lo mismo que un 96 % seguro."""
import math


def wilson(aciertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de Wilson al 95 %. Se comporta bien cerca de 0 y de 1, donde el intervalo normal falla."""
    if total == 0:
        return 0.0, 1.0
    p = aciertos / total
    centro = (p + z * z / (2 * total)) / (1 + z * z / total)
    margen = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return max(0.0, centro - margen), min(1.0, centro + margen)
