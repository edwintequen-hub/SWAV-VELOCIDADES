import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests

from app.services.sinoptico_directo_service import (
    SinopticoDirectoService,
)


class SinopticoR16Service:

    def __init__(
        self,
        max_intentos=3,
        espera_reintento=3,
        modo_remoto=None,
    ):

        self.root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        self.bridge_dir = (
            self.root
            / "backend"
            / "sinoptico_bridge"
        )

        self.bridge = (
            self.bridge_dir
            / "SinopticoBridge.exe"
        )

        self.max_intentos = int(
            max_intentos
        )

        self.espera_reintento = float(
            espera_reintento
        )

        self.bridge_url = str(
            os.getenv(
                "SWAV_BRIDGE_URL",
                ""
            )
        ).strip().rstrip("/")

        self.bridge_token = str(
            os.getenv(
                "SWAV_BRIDGE_TOKEN",
                ""
            )
        ).strip()

        self.sinoptico_report_secret = str(
            os.getenv(
                "SWAV_SINOPTICO_REPORT_SECRET",
                ""
            )
        ).strip()

        self.modo_directo = bool(
            self.sinoptico_report_secret
        )

        if modo_remoto is None:

            self.modo_remoto = bool(
                self.bridge_url
                and
                self.bridge_token
            )

        else:

            self.modo_remoto = bool(
                modo_remoto
            )


    # ======================================================
    # BRIDGE LOCAL WINDOWS
    # ======================================================

    def _ejecutar_bridge_local(
        self,
        usuario,
        unidad,
        fecha,
        hora_desde,
        hora_hasta,
    ):

        with tempfile.NamedTemporaryFile(
            mode="w+",
            encoding="utf-8",
            suffix=".json",
            delete=False,
        ) as temporal:

            temporal_path = Path(
                temporal.name
            )

        try:

            with open(
                temporal_path,
                "w",
                encoding="utf-8",
                errors="replace",
            ) as salida:

                proceso = subprocess.run(
                    [
                        str(self.bridge),
                        "r16web",
                        usuario,
                        unidad,
                        str(fecha),
                        str(hora_desde),
                        str(hora_hasta),
                    ],
                    cwd=str(
                        self.bridge_dir
                    ),
                    stdout=salida,
                    stderr=None,
                    timeout=120,
                    check=False,
                )

            stdout = (
                temporal_path
                .read_text(
                    encoding="utf-8",
                    errors="replace",
                )
                .strip()
            )

            return (
                proceso.returncode,
                stdout,
            )

        finally:

            try:

                temporal_path.unlink(
                    missing_ok=True
                )

            except Exception:

                pass


    # ======================================================
    # BRIDGE REMOTO HTTPS
    # ======================================================

    def _ejecutar_bridge_remoto(
        self,
        usuario,
        unidad,
        fecha,
        hora_desde,
        hora_hasta,
    ):

        if not self.bridge_url:

            raise RuntimeError(
                "SWAV_BRIDGE_URL no configurado"
            )

        if not self.bridge_token:

            raise RuntimeError(
                "SWAV_BRIDGE_TOKEN no configurado"
            )

        url = (
            self.bridge_url
            + "/r16download"
        )

        payload = {
            "usuario": usuario,
            "unidad": unidad,
            "fecha": str(fecha),
            "hora_desde": str(hora_desde),
            "hora_hasta": str(hora_hasta),
        }

        headers = {
            "X-SWAV-TOKEN":
                self.bridge_token
        }

        respuesta = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=180,
        )

        if respuesta.status_code != 200:

            raise RuntimeError(
                "Bridge remoto fallo. "
                f"HTTP={respuesta.status_code} "
                f"respuesta={respuesta.text[:500]!r}"
            )

        if len(respuesta.content) < 1000:

            raise RuntimeError(
                "Bridge remoto devolvio "
                "archivo demasiado pequeno: "
                f"{len(respuesta.content)} bytes"
            )

        unidad_header = str(
            respuesta.headers.get(
                "X-SWAV-UNIDAD",
                ""
            )
        ).strip().upper()

        validado_header = str(
            respuesta.headers.get(
                "X-SWAV-VALIDADO",
                ""
            )
        ).strip().lower()

        if unidad_header and (
            unidad_header != unidad
        ):

            raise RuntimeError(
                "Bridge remoto devolvio "
                f"unidad {unidad_header}, "
                f"se esperaba {unidad}"
            )

        if validado_header != "true":

            raise RuntimeError(
                "Bridge remoto devolvio "
                "archivo no validado"
            )

        carpeta_temporal = (
            self.root
            / "backend"
            / "uploads"
            / "r16_remoto"
        )

        carpeta_temporal.mkdir(
            parents=True,
            exist_ok=True,
        )

        nombre = (
            f"R16_{unidad}_"
            f"{str(fecha).replace('/', '-')}_"
            f"{str(hora_desde).replace(':', '')}_"
            f"{str(hora_hasta).replace(':', '')}.csv"
        )

        archivo = (
            carpeta_temporal
            / nombre
        )

        archivo.write_bytes(
            respuesta.content
        )

        if not archivo.exists():

            raise RuntimeError(
                "No fue posible guardar "
                "el R1.6 remoto"
            )

        if archivo.stat().st_size < 1000:

            raise RuntimeError(
                "R1.6 remoto guardado "
                "con tamano invalido"
            )

        return {
            "ok": True,
            "validado": True,
            "archivo": str(
                archivo.resolve()
            ),
            "modo": "REMOTO",
            "bytes":
                archivo.stat().st_size,
        }


    # ======================================================
    # DESCARGA PRINCIPAL
    # ======================================================

    def descargar(
        self,
        usuario,
        unidad,
        fecha,
        hora_desde,
        hora_hasta,
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

            raise RuntimeError(
                "Usuario Sinoptico vacio"
            )

        if unidad not in (
            "U8",
            "U9",
        ):

            raise RuntimeError(
                f"Unidad no soportada: "
                f"{unidad}"
            )


        # ==================================================
        # MODO DIRECTO PYTHON
        # ==================================================

        if self.modo_directo:

            servicio_directo = (
                SinopticoDirectoService(
                    secreto=self.sinoptico_report_secret,
                    timeout=90,
                )
            )

            return servicio_directo.descargar(
                usuario=usuario,
                unidad=unidad,
                fecha=fecha,
                hora_desde=hora_desde,
                hora_hasta=hora_hasta,
            )


        # ==================================================
        # MODO REMOTO
        # ==================================================

        if self.modo_remoto:

            return (
                self._ejecutar_bridge_remoto(
                    usuario=usuario,
                    unidad=unidad,
                    fecha=fecha,
                    hora_desde=hora_desde,
                    hora_hasta=hora_hasta,
                )
            )


        # ==================================================
        # MODO LOCAL
        # ==================================================

        if not self.bridge.exists():

            raise FileNotFoundError(
                "No existe SinopticoBridge.exe: "
                f"{self.bridge}"
            )

        ultimo_error = None

        for intento in range(
            1,
            self.max_intentos + 1,
        ):

            print(
                f"R1.6 SINOPTICO - "
                f"INTENTO {intento}/"
                f"{self.max_intentos}"
            )

            try:

                returncode, stdout = (
                    self._ejecutar_bridge_local(
                        usuario=usuario,
                        unidad=unidad,
                        fecha=fecha,
                        hora_desde=hora_desde,
                        hora_hasta=hora_hasta,
                    )
                )

            except subprocess.TimeoutExpired:

                ultimo_error = (
                    "Python excedio timeout "
                    "esperando al Bridge"
                )

            else:

                if returncode == 0:

                    try:

                        data = json.loads(
                            stdout
                        )

                    except json.JSONDecodeError as exc:

                        raise RuntimeError(
                            "Bridge no devolvio "
                            "JSON valido. "
                            f"stdout={stdout!r}"
                        ) from exc

                    if not data.get("ok"):

                        raise RuntimeError(
                            "Bridge devolvio "
                            "ok=false: "
                            + json.dumps(
                                data,
                                ensure_ascii=False,
                            )
                        )

                    if not data.get(
                        "validado"
                    ):

                        raise RuntimeError(
                            "Bridge devolvio "
                            "archivo R1.6 "
                            "no validado"
                        )

                    archivo = Path(
                        str(
                            data.get(
                                "archivo",
                                "",
                            )
                        )
                    )

                    if not archivo.exists():

                        raise RuntimeError(
                            "Bridge reporto "
                            "archivo inexistente: "
                            f"{archivo}"
                        )

                    if (
                        archivo.stat().st_size
                        < 1000
                    ):

                        raise RuntimeError(
                            "Archivo R1.6 "
                            "demasiado pequeno: "
                            f"{archivo.stat().st_size} "
                            "bytes"
                        )

                    data["archivo"] = str(
                        archivo.resolve()
                    )

                    data["intento"] = (
                        intento
                    )

                    data["modo"] = "LOCAL"

                    return data

                ultimo_error = (
                    "Bridge R1.6 fallo. "
                    f"returncode={returncode} "
                    f"stdout={stdout!r}"
                )

                texto_error = (
                    stdout or ""
                ).lower()

                es_timeout = (
                    "tiempo de espera"
                    in texto_error
                    or
                    "timeout"
                    in texto_error
                )

                if not es_timeout:

                    raise RuntimeError(
                        ultimo_error
                    )

            if (
                intento
                < self.max_intentos
            ):

                print(
                    "Timeout Sinoptico. "
                    f"Reintentando en "
                    f"{self.espera_reintento:g} "
                    "segundos..."
                )

                time.sleep(
                    self.espera_reintento
                )

        raise RuntimeError(
            "No fue posible descargar "
            "R1.6 despues de "
            f"{self.max_intentos} intentos. "
            f"Ultimo error: {ultimo_error}"
        )


