import json
from pathlib import Path

from ..puertos import Cliente, Cuenta


class ClientesJson:
    def __init__(self, ruta: Path):
        datos = json.loads(ruta.read_text(encoding="utf-8"))["clientes"]
        self._clientes = [
            (Cliente(c["id"], c["nombre"], c["dni"], tuple(Cuenta(**k) for k in c["cuentas"])), c["token_demo"]) for c in datos
        ]

    def por_id(self, cliente_id):
        return next((c for c, _ in self._clientes if c.id == cliente_id), None)

    def por_token(self, token):
        return next((c for c, t in self._clientes if t == token), None)

    def por_dni(self, dni):
        return next((c for c, _ in self._clientes if c.dni == dni), None)
