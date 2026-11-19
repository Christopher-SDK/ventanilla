"""Borra las grabaciones que ninguna corrida usa (suite limpia + las 7 fallas). Uso: uv run python scripts/podar_grabaciones.py"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from ventanilla.fallas import FALLAS

RAIZ = Path(__file__).resolve().parents[1]

with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False) as reg:
    entorno = {**os.environ, "VENTANILLA_REGISTRO_USO": reg.name, "VENTANILLA_MODO": "reproducir"}
    for falla in [None, *FALLAS]:
        args = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *(["--falla", falla] if falla else [])]
        subprocess.run(args, cwd=RAIZ, env=entorno, stdout=subprocess.DEVNULL)
    usadas = set(Path(reg.name).read_text().split())

todas = list((RAIZ / "grabaciones").glob("*/*.json"))
sobran = [p for p in todas if p.stem not in usadas]
for p in sobran:
    p.unlink()
for d in (RAIZ / "grabaciones").iterdir():
    if d.is_dir() and not any(d.iterdir()):
        d.rmdir()
print(f"grabaciones: {len(todas)} → {len(todas) - len(sobran)} (se borraron {len(sobran)} sin uso)")
