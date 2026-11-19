"""Corre Locust sin interfaz contra la API grabada y falla si se pasan los umbrales. Uso: uv run python scripts/carga.py"""
import csv
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parents[1]
P95_MAX_MS = int(os.environ.get("CARGA_P95_MS", "300"))
SALIDA = RAIZ / "reporte" / "carga"
SALIDA.mkdir(parents=True, exist_ok=True)
import socket

with socket.socket() as libre:  # un puerto libre: nunca mide a otro servidor que ya ocupe el 8765
    libre.bind(("127.0.0.1", 0))
    puerto = str(libre.getsockname()[1])
entorno = {**os.environ, "VENTANILLA_MODO": "reproducir", "VENTANILLA_POR_MINUTO": "100000"}
api = subprocess.Popen([sys.executable, "-m", "uvicorn", "ventanilla.adaptadores.api:app_desde_entorno", "--factory", "--port", puerto,
                        "--log-level", "warning"], cwd=RAIZ, env=entorno)
try:
    for _ in range(100):
        if api.poll() is not None:
            sys.exit(f"carga: la API no arrancó (código {api.returncode})")
        try:
            if httpx.get(f"http://127.0.0.1:{puerto}/api/salud").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.2)
    else:
        sys.exit("carga: la API no respondió /api/salud en 20 s")
    subprocess.run([sys.executable, "-m", "locust", "-f", "carga/locustfile.py", "--headless", "-u", "20", "-r", "10", "-t", os.environ.get("CARGA_TIEMPO", "30s"),
                    "--host", f"http://127.0.0.1:{puerto}", "--csv", str(SALIDA / "locust"), "--only-summary"], cwd=RAIZ, check=False)
finally:
    api.terminate()

fila = next(r for r in csv.DictReader(open(SALIDA / "locust_stats.csv")) if r["Name"] == "Aggregated")
total, fallas, p95 = int(fila["Request Count"]), int(fila["Failure Count"]), float(fila["95%"])
print(f"carga: {total} peticiones, {fallas} fallas, p95 {p95:.0f} ms (máximo {P95_MAX_MS} ms)")
sys.exit(0 if total > 0 and fallas == 0 and p95 <= P95_MAX_MS else 1)
