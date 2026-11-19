"""Borra las grabaciones que ninguna corrida usa (suite limpia, las 7 fallas, promptfoo y los datos de la página demo). Uso: uv run python scripts/podar_grabaciones.py"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from ventanilla.fallas import FALLAS

RAIZ = Path(__file__).resolve().parents[1]

with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False) as reg:
    entorno = {**os.environ, "VENTANILLA_REGISTRO_USO": reg.name, "VENTANILLA_MODO": "reproducir"}
    for falla in [None, *FALLAS]:
        args = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *(["--falla", falla] if falla else [])]
        subprocess.run(args, cwd=RAIZ, env=entorno, stdout=subprocess.DEVNULL)
    # la página demo genera sus datos con el sistema real (scripts/datos_web.py)
    subprocess.run([sys.executable, "scripts/datos_web.py"], cwd=RAIZ, env=entorno, stdout=subprocess.DEVNULL, check=True)
    # promptfoo también reproduce grabaciones a través de la API
    api = subprocess.Popen([sys.executable, "-m", "uvicorn", "ventanilla.adaptadores.api:app_desde_entorno", "--factory", "--port", "8766",
                            "--log-level", "warning"], cwd=RAIZ, env={**entorno, "VENTANILLA_POR_MINUTO": "100000"})
    try:
        time.sleep(3)
        subprocess.run(["npx", "-y", "promptfoo@0.126.0", "eval", "-c", "promptfooconfig.yaml", "--no-cache", "-j", "4"], cwd=RAIZ / "evals" / "promptfoo",
                       env={**entorno, "VENTANILLA_URL": "http://127.0.0.1:8766", "PROMPTFOO_DISABLE_TELEMETRY": "1"}, stdout=subprocess.DEVNULL, check=True)
    finally:
        api.terminate()
    usadas = set(Path(reg.name).read_text().split())

todas = list((RAIZ / "grabaciones").glob("*/*.json"))
sobran = [p for p in todas if p.stem not in usadas]
for p in sobran:
    p.unlink()
for d in (RAIZ / "grabaciones").iterdir():
    if d.is_dir() and not any(d.iterdir()):
        d.rmdir()
print(f"grabaciones: {len(todas)} → {len(todas) - len(sobran)} (se borraron {len(sobran)} sin uso)")
