"""Grabar y reproducir llamadas al modelo: la CI corre sin Ollama y siempre igual.

Cada llamada se identifica por el hash de su petición completa (modelo, mensajes, opciones).
Modos:
  reproducir  usa solo lo grabado; si falta una grabación, falla y dice cómo crearla (por defecto)
  grabar      llama al modelo y guarda la respuesta
  auto        reproduce si existe; si no, llama y guarda
  vivo        llama al modelo sin guardar nada
"""
import hashlib
import json
import os
from pathlib import Path

MODOS = ("reproducir", "grabar", "auto", "vivo")


class GrabacionFaltante(RuntimeError):
    pass


def clave(peticion: dict) -> str:
    return hashlib.sha256(json.dumps(peticion, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Grabadora:
    def __init__(self, carpeta: Path, modo: str = "reproducir"):
        if modo not in MODOS:
            raise ValueError(f"modo {modo!r}: usa uno de {MODOS}")
        self.carpeta, self.modo = carpeta, modo
        self.usadas: set[str] = set()

    def ruta(self, k: str) -> Path:
        return self.carpeta / k[:2] / f"{k}.json"

    def llamar(self, peticion: dict, real):
        k = clave(peticion)
        self.usadas.add(k)
        if registro := os.environ.get("VENTANILLA_REGISTRO_USO"):  # lo usa scripts/podar_grabaciones.py
            with open(registro, "a", encoding="utf-8") as f:
                f.write(k + "\n")
        ruta = self.ruta(k)
        if self.modo in ("reproducir", "auto") and ruta.exists():
            return json.loads(ruta.read_text(encoding="utf-8"))["respuesta"]
        if self.modo == "reproducir":
            raise GrabacionFaltante(
                f"No hay grabación para esta llamada ({k[:12]}). Con Ollama encendido, corre con VENTANILLA_MODO=auto para crearla."
            )
        respuesta = real(peticion)
        if self.modo != "vivo":
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_text(json.dumps({"peticion": peticion, "respuesta": respuesta}, ensure_ascii=False, indent=1), encoding="utf-8")
        return respuesta


class ChatGrabado:
    def __init__(self, real, grabadora: Grabadora):
        self.real, self.grabadora, self.nombre = real, grabadora, real.nombre

    def generar(self, mensajes, semilla=7):
        return self.grabadora.llamar(self.real.peticion(mensajes, semilla), self.real.enviar)


class EmbeddingsGrabados:
    def __init__(self, real, grabadora: Grabadora):
        self.real, self.grabadora, self.nombre = real, grabadora, real.nombre

    def vectores(self, textos):
        return self.grabadora.llamar(self.real.peticion(textos), self.real.enviar)
