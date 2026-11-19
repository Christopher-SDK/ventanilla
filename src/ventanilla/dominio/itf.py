"""ITF: 0,005 % del monto, truncado al múltiplo de cinco céntimos inferior (TUO Ley 28194, art. 13)."""
from decimal import Decimal

TASA = Decimal("0.005")  # en porcentaje


def calcular(monto_centimos: int) -> int:
    if monto_centimos < 0:
        raise ValueError("el monto no puede ser negativo")
    bruto = monto_centimos * 5 // 100_000  # 0,005 % en céntimos, sin fracciones
    return bruto // 5 * 5
