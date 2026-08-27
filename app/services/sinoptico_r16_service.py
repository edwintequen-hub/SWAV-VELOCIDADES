import json
import subprocess
import tempfile
import time
from pathlib import Path


class SinopticoR16Service:

    def __init__(
        self,
        max_intentos=3,
        espera_reintento=3,
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


    def _ejecutar_bridge(
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

                    # IMPORTANTE:
                    # capture_output=True fue descartado
                    # porque produjo timeout con este Bridge.
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
                f"Unidad no soportada: {unidad}"
            )

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
                    self._ejecutar_bridge(
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

                    return data

                ultimo_error = (
                    "Bridge R1.6 fallo. "
                    f"returncode={returncode} "
                    f"stdout={stdout!r}"
                )

                # Solo reintentamos errores
                # transitorios de red/timeout.
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
