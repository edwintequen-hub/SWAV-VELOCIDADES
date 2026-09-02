"""
=========================================================
SWAV
COORDINADOR DE OPERACIONES DE ESCRITURA
=========================================================

Evita que dos procesos pesados de escritura SWAV se
ejecuten simultaneamente dentro de la misma instancia.

Protege:
- Anexo 3
- Anexo 4
- R1.6 manual
- R1.6 automatico
- Reprocesamientos

IMPORTANTE:
Este bloqueo es por proceso Python.
Para produccion multi-instancia con PostgreSQL se podra
reemplazar/complementar con advisory locks de PostgreSQL.
=========================================================
"""

import threading
from contextlib import contextmanager


class OperacionSWAVEnCurso(Exception):
    pass


class CoordinadorOperacionesSWAV:

    def __init__(self):

        self._lock = threading.RLock()

        self._estado_lock = threading.Lock()

        self._operacion_actual = None


    @property
    def operacion_actual(self):

        with self._estado_lock:

            return self._operacion_actual


    def _establecer_operacion(
        self,
        operacion
    ):

        with self._estado_lock:

            self._operacion_actual = operacion


    @contextmanager
    def operacion(
        self,
        nombre,
        esperar=True
    ):

        adquirido = self._lock.acquire(
            blocking=esperar
        )

        if not adquirido:

            actual = (
                self.operacion_actual
                or "otra operacion SWAV"
            )

            raise OperacionSWAVEnCurso(
                "No se puede iniciar "
                + str(nombre)
                + ". Actualmente se esta ejecutando: "
                + str(actual)
                + "."
            )

        anterior = self.operacion_actual

        try:

            self._establecer_operacion(
                nombre
            )

            print(
                "[SWAV LOCK] INICIO:",
                nombre
            )

            yield

        finally:

            self._establecer_operacion(
                anterior
            )

            print(
                "[SWAV LOCK] FIN:",
                nombre
            )

            self._lock.release()


coordinador_swav = CoordinadorOperacionesSWAV()
