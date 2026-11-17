"""Limitador de peticiones por IP (ventana deslizante en memoria) para los endpoints sensibles
(inicio de sesión, CAPTCHA, registro). Complementa el bloqueo por cuenta: frena el relleno de
credenciales contra MUCHAS cuentas desde una misma IP.

Nota: el estado vive en el proceso. Con varios workers de gunicorn cada uno lleva su conteo; para
un límite global se debe usar un almacén compartido (p. ej. Redis) o el proxy inverso.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Regla:
    maximo: int
    ventana_s: int


class LimitadorPeticiones:
    def __init__(self, reloj=time.monotonic, max_claves: int = 10000):
        self._reloj, self._max_claves = reloj, max_claves
        self._eventos: dict[str, deque] = {}
        self._lock = threading.Lock()

    def permitir(self, clave: str, regla: Regla) -> tuple[bool, int]:
        """Registra un intento. Devuelve (permitido, segundos de espera sugeridos)."""
        ahora = self._reloj()
        with self._lock:
            cola = self._eventos.setdefault(clave, deque())
            while cola and cola[0] <= ahora - regla.ventana_s:
                cola.popleft()
            if len(cola) >= regla.maximo:
                return False, max(1, int(cola[0] + regla.ventana_s - ahora) + 1)
            cola.append(ahora)
            if len(self._eventos) > self._max_claves:          # evita crecimiento ilimitado de memoria
                self._purgar(ahora, regla.ventana_s)
            return True, 0

    def _purgar(self, ahora: float, ventana: int) -> None:
        for clave in [k for k, c in self._eventos.items() if not c or c[-1] <= ahora - ventana]:
            del self._eventos[clave]

    def reiniciar(self) -> None:
        with self._lock:
            self._eventos.clear()
