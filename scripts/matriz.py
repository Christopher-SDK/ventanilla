"""Matriz de detección: la suite limpia y una corrida por cada falla sembrada.

Uso: uv run python scripts/matriz.py [--json ruta]   (escribe reporte/matriz.json y reporte/matriz.md)
"""
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from ventanilla.fallas import FALLAS

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "reporte"
CAPAS = {
    "unitarias": "Unitarias", "propiedades": "Propiedades", "recuperacion": "Recuperación", "seguridad": "Seguridad",
    "privacidad": "Privacidad", "regulacion": "Regulación", "modelo": "Modelo real", "api": "API y contrato",
    "ui": "Interfaz", "arquitectura": "Arquitectura", "suministro": "Suministro",
}


def correr(falla: str | None) -> dict:
    xml = SALIDA / f"junit-{falla or 'limpio'}.xml"
    args = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}", *(["--falla", falla] if falla else [])]
    t0 = time.monotonic()
    subprocess.run(args, cwd=RAIZ, env={**os.environ, "VENTANILLA_MODO": "reproducir", "DEEPEVAL_TELEMETRY_OPT_OUT": "1"}, stdout=subprocess.DEVNULL)
    segundos = round(time.monotonic() - t0, 1)
    total, fallidas = 0, []
    for caso in ET.parse(xml).iter("testcase"):
        total += 1
        error = caso.find("failure") if caso.find("failure") is not None else caso.find("error")
        if error is not None:
            capa = CAPAS.get(caso.get("classname", "").split(".")[1] if caso.get("classname", "").count(".") > 1 else "", "?")
            fallidas.append({"prueba": f"{caso.get('classname').split('.')[-1]}::{caso.get('name')}", "capa": capa,
                             "mensaje": (error.get("message") or "").splitlines()[0][:200]})
    return {"falla": falla, "total": total, "fallidas": len(fallidas), "segundos": segundos, "capas": sorted({f["capa"] for f in fallidas}),
            "primera": fallidas[0] if fallidas else None, "detalle": fallidas[:12]}


def main():
    SALIDA.mkdir(exist_ok=True)
    limpio = correr(None)
    filas = [{**correr(f), "descripcion": d} for f, d in FALLAS.items()]
    detectadas = sum(f["fallidas"] > 0 for f in filas)
    datos = {"limpio": limpio, "fallas": filas, "detectadas": detectadas, "total_fallas": len(filas), "fecha": time.strftime("%Y-%m-%d")}
    destino = Path(sys.argv[sys.argv.index("--json") + 1]) if "--json" in sys.argv else SALIDA / "matriz.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=1))

    md = [f"## Matriz de detección: {detectadas}/{len(filas)} fallas atrapadas", "",
          f"Suite limpia: {limpio['total']} pruebas, {limpio['fallidas']} fallas, {limpio['segundos']} s.", "",
          "| Falla | Pruebas que fallan | Capas | Primera en fallar |", "|---|---|---|---|"]
    for f in filas:
        primera = f"`{f['primera']['prueba'][:70]}`" if f["primera"] else "— **no detectada**"
        md.append(f"| {f['falla']} | {f['fallidas']} | {', '.join(f['capas'])} | {primera} |")
    (SALIDA / "matriz.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(0 if limpio["fallidas"] == 0 and detectadas == len(filas) else 1)


if __name__ == "__main__":
    main()
