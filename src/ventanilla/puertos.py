"""Lo que el dominio necesita del mundo exterior. Los adaptadores lo implementan."""
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Mensaje:
    rol: str  # system | user | assistant
    texto: str


class ModeloDeLenguaje(Protocol):
    nombre: str

    def generar(self, mensajes: list[Mensaje], semilla: int = 7) -> str: ...


class Embeddings(Protocol):
    nombre: str

    def vectores(self, textos: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class Cuenta:
    tipo: str
    numero: str
    saldo_centimos: int


@dataclass(frozen=True)
class Cliente:
    id: str
    nombre: str
    dni: str
    cuentas: tuple[Cuenta, ...]


class Clientes(Protocol):
    def por_id(self, cliente_id: str) -> Cliente | None: ...

    def por_token(self, token: str) -> Cliente | None: ...

    def por_dni(self, dni: str) -> Cliente | None: ...
