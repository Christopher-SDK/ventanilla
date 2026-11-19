"""Compara los modelos de Ollama con modelos.lock.json (job nocturno). Uso: uv run python scripts/verificar_modelos.py"""
import json
import os
import sys
from pathlib import Path

import httpx

lock = json.loads((Path(__file__).resolve().parents[1] / "modelos.lock.json").read_text())
host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
instalados = {m["name"]: m["digest"] for m in httpx.get(f"{host}/api/tags", timeout=10).json()["models"]}
version = httpx.get(f"{host}/api/version", timeout=10).json()["version"]
problemas = [f"Ollama {version}, se fijó {lock['ollama']}"] if version != lock["ollama"] else []
for m in lock["modelos"]:
    real = instalados.get(m["nombre"])
    if real != m["digest"]:
        problemas.append(f"{m['nombre']}: digest {real or 'no instalado'} ≠ {m['digest']}")
print("\n".join(problemas) or "modelos y versión de Ollama coinciden con modelos.lock.json")
sys.exit(1 if problemas else 0)
