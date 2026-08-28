import hashlib
import os
import re
from datetime import datetime
from pathlib import Path

import requests


class SinopticoDirectoService:

    URL_REPORTE = (
        "https://snptc.tstgo.cl:8543/"
        "DagJRelay/DagJRelayServlet10.do"
    )

    OPERADORES = {
        "U8": "3613",
        "U9": "3614",
    }


    def __init__(
        self,
        secreto: str,
        timeout: int = 90,
    ):

        self.secreto = str(
            secreto
            or os.getenv(
                "SWAV_SINOPTICO_REPORT_SECRET",
                ""
            )
        ).strip()

        self.timeout = timeout

        if len(self.secreto) < 20:
            raise ValueError(
                "Secreto Sinoptico invalido"
            )


    def _construir_post(
        self,
        usuario: str,
        unidad: str,
        fecha: str,
        hora_desde: str,
        hora_hasta: str,
    ):

        usuario = str(
            usuario or ""
        ).strip()

        unidad = str(
            unidad or ""
        ).strip().upper()

        fecha = str(
            fecha or ""
        ).strip()

        hora_desde = str(
            hora_desde or ""
        ).strip()

        hora_hasta = str(
            hora_hasta or ""
        ).strip()


        if not usuario:
            raise ValueError(
                "Usuario Sinoptico vacio"
            )


        if unidad not in self.OPERADORES:
            raise ValueError(
                "Unidad no soportada: "
                + unidad
            )


        # ==========================================
        # VALIDAR FECHA
        # ==========================================

        datetime.strptime(
            fecha,
            "%d/%m/%Y",
        )


        # ==========================================
        # VALIDAR HORAS
        #
        # Se aceptan:
        # HH:mm
        # HH:mm:ss
        # ==========================================

        def validar_hora(valor):

            formatos = [
                "%H:%M",
                "%H:%M:%S",
            ]

            for formato in formatos:

                try:

                    datetime.strptime(
                        valor,
                        formato,
                    )

                    return

                except ValueError:

                    pass

            raise ValueError(
                "Hora invalida: "
                + valor
            )


        validar_hora(
            hora_desde
        )

        validar_hora(
            hora_hasta
        )


        operador = (
            self.OPERADORES[
                unidad
            ]
        )


        parametros = [

            "rpt=RptBusEnServicio10xCsv",

            "export=Csv",

            "extension=csv",

            "dlm=TAB",

            "Usr_Lgn="
            + usuario,

            "In_IdOperador="
            + operador,

            "In_IdServicio=-99",

            "In_FechaInicial="
            + fecha,

            "In_FechaFinal="
            + fecha,

            "In_HoraInicial="
            + hora_desde,

            "In_HoraFinal="
            + hora_hasta,

            "In_IdTolerancia=15",

            "separator=.,",
        ]


        partes_post = [
            parametros[0]
        ]

        partes_digest = []


        for indice in range(
            1,
            len(parametros),
        ):

            prefijo = (
                f"{indice:03d}"
            )

            elemento = (
                prefijo
                +
                parametros[indice]
            )

            partes_post.append(
                elemento
            )

            partes_digest.append(
                elemento
            )


        cadena_post = "&".join(
            partes_post
        )

        cadena_digest = "&".join(
            partes_digest
        )


        entrada_firma = (
            cadena_digest
            +
            self.secreto
        )


        digest = hashlib.md5(
            entrada_firma.encode(
                "utf-8"
            )
        ).hexdigest()


        post_final = (
            cadena_post
            +
            "&digest="
            +
            digest
        )


        return (
            operador,
            post_final,
        )


    def descargar(
        self,
        usuario: str,
        unidad: str,
        fecha: str,
        hora_desde: str,
        hora_hasta: str,
        carpeta_destino=None,
    ):

        unidad = str(
            unidad or ""
        ).strip().upper()


        operador, post_final = (
            self._construir_post(
                usuario=usuario,
                unidad=unidad,
                fecha=fecha,
                hora_desde=hora_desde,
                hora_hasta=hora_hasta,
            )
        )


        respuesta = requests.post(

            self.URL_REPORTE,

            data=post_final.encode(
                "utf-8"
            ),

            headers={

                "Content-Type":
                    "application/x-www-form-urlencoded",

                "User-Agent":
                    "Mozilla/5.0",

                "Accept":
                    "*/*",
            },

            timeout=self.timeout,
        )


        if respuesta.status_code != 200:

            raise RuntimeError(
                "Sinoptico respondio HTTP "
                +
                str(
                    respuesta.status_code
                )
            )


        contenido = (
            respuesta.content
        )


        if not contenido:

            raise RuntimeError(
                "Sinoptico devolvio "
                "un archivo vacio"
            )


        # ==========================================
        # DECODIFICAR
        # ==========================================

        try:

            texto = contenido.decode(
                "utf-8-sig"
            )

        except UnicodeDecodeError:

            texto = contenido.decode(
                "cp1252",
                errors="replace",
            )


        lineas = (
            texto.splitlines()
        )


        filas_r16 = [

            linea

            for linea in lineas

            if re.match(
                r"^T[0-9]",
                linea.strip(),
                re.IGNORECASE,
            )
        ]


        encabezado_ok = (

            "R1.6"
            in texto[:5000]

            or

            "BUSES EN SERVICIO"
            in texto[:5000].upper()

        )


        # ==========================================
        # VALIDACION
        # ==========================================

        validado = (

            len(contenido) > 1000

            and

            len(filas_r16) > 0

        )


        if not validado:

            raise RuntimeError(
                "La respuesta de Sinoptico "
                "no pudo certificarse como R1.6"
            )


        # ==========================================
        # CARPETA DESTINO
        # ==========================================

        if carpeta_destino is None:

            raiz = (
                Path(__file__)
                .resolve()
                .parents[2]
            )

            carpeta_destino = (
                raiz
                /
                "backend"
                /
                "uploads"
                /
                "r16_directo"
            )

        else:

            carpeta_destino = Path(
                carpeta_destino
            )


        carpeta_destino.mkdir(
            parents=True,
            exist_ok=True,
        )


        nombre = (

            "R16_DIRECTO_"

            +
            unidad

            +
            "_"

            +
            fecha.replace(
                "/",
                ""
            )

            +
            "_"

            +
            hora_desde.replace(
                ":",
                ""
            )

            +
            "_"

            +
            hora_hasta.replace(
                ":",
                ""
            )

            +
            ".csv"
        )


        archivo = (
            carpeta_destino
            /
            nombre
        )


        archivo.write_bytes(
            contenido
        )


        return {

            "ok": True,

            "validado": True,

            "modo":
                "DIRECTO_PYTHON",

            "unidad":
                unidad,

            "operador":
                operador,

            "archivo":
                str(archivo),

            "bytes":
                len(contenido),

            "lineas":
                len(lineas),

            "filas_r16":
                len(filas_r16),

            "encabezado_ok":
                encabezado_ok,

            "content_type":
                respuesta.headers.get(
                    "Content-Type"
                ),
        }

