"""
SWAV

Archivo:
backend/app/utils/parser_rutas.py

HM-006

Objetivo:
Interpretar rutas provenientes del R1.6.

Responsabilidad:
    - Interpretar la ruta.
    - Extraer Código TS.
    - Extraer sentido.
    - Conservar ruta original.
    - No consulta Base de Datos.
    - No consulta INFO.
    - No consulta Catálogo Maestro.
"""

import re


class ParserRutas:
    """
    Parser de rutas provenientes del R1.6.
    """

    @staticmethod
    def interpretar(ruta: str):
        """
        Interpreta una ruta del R1.6.

        Ejemplo:

            T841 E0 06R

        Resultado:

            codigo_ts = 841E
            sentido   = R
        """

        if ruta is None:
            return None

        ruta_original = str(ruta).strip()

        if not ruta_original:
            return None

        # Normalizar espacios y mayúsculas
        ruta_normalizada = (
            " ".join(
                ruta_original.upper().split()
            )
        )

        partes = ruta_normalizada.split()

        # -------------------------------------------------
        # SENTIDO
        # -------------------------------------------------

        sentido = ""

        if partes:
            ultimo = partes[-1]

            if ultimo.endswith("I"):
                sentido = "I"

            elif ultimo.endswith("R"):
                sentido = "R"

        # -------------------------------------------------
        # CÓDIGO TS
        # -------------------------------------------------
        #
        # Ejemplo:
        #
        # T841 E0 06R
        #
        # T841 -> código base 841
        # E0   -> identifica servicio empresarial E
        #
        # Resultado:
        #
        # 841E
        #
        # -------------------------------------------------

        codigo_ts = None

        if partes:

            primer_token = partes[0]

            match_numero = re.match(
                r"^T?(\d+)$",
                primer_token
            )

            if match_numero:

                codigo_base = match_numero.group(1)

                # Ruta tipo:
                # T841 E0 06R
                if len(partes) >= 2 and re.match(
                    r"^E\d*$",
                    partes[1]
                ):
                    codigo_ts = f"{codigo_base}E"

                # Ruta tipo:
                # T841 00R
                else:
                    codigo_ts = codigo_base

        return {
            "ruta_original": ruta_normalizada,
            "codigo_ts": codigo_ts,
            "sentido": sentido,
            "partes": partes,
            "cantidad_partes": len(partes),
        }