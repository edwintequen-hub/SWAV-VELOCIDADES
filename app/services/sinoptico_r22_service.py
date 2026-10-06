import json
import subprocess
import tempfile
from pathlib import Path


class SinopticoR22Service:
    """
    Descargador aislado R2.2 para Flota.

    - Usa el Bridge V9 ya certificado.
    - No modifica BD.
    - No reemplaza el Bridge productivo R1.6.
    - No interpreta velocidades.
    """

    def __init__(
        self,
        max_intentos=2,
        espera_reintento=2,
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
            / "SinopticoBridge_V9_DIRECTO_PRUEBA.exe"
        )

        self.max_intentos = int(max_intentos)
        self.espera_reintento = float(
            espera_reintento
        )

    @staticmethod
    def _normalizar_fecha_archivo(fecha):
        texto = str(fecha or "").strip()

        if not texto:
            raise RuntimeError(
                "Fecha R2.2 vacia"
            )

        if "/" in texto:
            partes = texto.split("/")

            if len(partes) != 3:
                raise RuntimeError(
                    f"Fecha R2.2 invalida: {texto}"
                )

            dd, mm, yyyy = partes

        elif "-" in texto:
            partes = texto.split("-")

            if len(partes) != 3:
                raise RuntimeError(
                    f"Fecha R2.2 invalida: {texto}"
                )

            if len(partes[0]) == 4:
                yyyy, mm, dd = partes
            else:
                dd, mm, yyyy = partes

        else:
            raise RuntimeError(
                f"Fecha R2.2 invalida: {texto}"
            )

        return (
            f"{int(dd):02d}"
            f"{int(mm):02d}"
            f"{int(yyyy):04d}"
        )

    def ruta_archivo_esperado(
        self,
        unidad,
        fecha,
    ):
        unidad = str(
            unidad or ""
        ).strip().upper()

        fecha_archivo = (
            self._normalizar_fecha_archivo(
                fecha
            )
        )

        return (
            self.bridge_dir
            / (
                f"R2_2_{unidad}_"
                f"{fecha_archivo}_V9.csv"
            )
        )

    def descargar(
        self,
        usuario,
        password,
        unidad,
        fecha,
    ):
        usuario = str(
            usuario or ""
        ).strip()

        password = str(
            password or ""
        )

        unidad = str(
            unidad or ""
        ).strip().upper()

        fecha = str(
            fecha or ""
        ).strip()

        if not usuario:
            raise RuntimeError(
                "Usuario Sinoptico vacio"
            )

        if not password:
            raise RuntimeError(
                "Clave Sinoptico vacia"
            )

        if unidad not in ("U8", "U9"):
            raise RuntimeError(
                f"Unidad no soportada: {unidad}"
            )

        if not fecha:
            raise RuntimeError(
                "Fecha R2.2 vacia"
            )

        if not self.bridge.exists():
            raise FileNotFoundError(
                "No existe Bridge V9 R2.2: "
                f"{self.bridge}"
            )

        ruta_esperada = (
            self.ruta_archivo_esperado(
                unidad=unidad,
                fecha=fecha,
            )
        )

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
                        "r22download",
                        usuario,
                        unidad,
                        fecha,
                    ],
                    cwd=str(self.bridge_dir),
                    input=password + "\n",
                    text=True,
                    stdout=salida,
                    stderr=None,
                    timeout=180,
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

            if proceso.returncode != 0:
                raise RuntimeError(
                    "Bridge R2.2 fallo. "
                    f"returncode={proceso.returncode}. "
                    f"stdout={stdout[-1000:]!r}"
                )

            try:
                data = json.loads(stdout)

            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "Bridge R2.2 no devolvio "
                    "JSON valido por stdout. "
                    f"stdout={stdout[-1000:]!r}"
                ) from exc

            if not data.get("ok"):
                raise RuntimeError(
                    "Bridge R2.2 respondio error: "
                    f"{data}"
                )

            ruta_reportada = (
                data.get("zip_path")
                or
                data.get("archivo")
            )

            if ruta_reportada:
                ruta_archivo = Path(
                    ruta_reportada
                )
            else:
                ruta_archivo = ruta_esperada

            if not ruta_archivo.exists():
                raise RuntimeError(
                    "Bridge R2.2 termino OK "
                    "pero no existe el CSV: "
                    f"{ruta_archivo}"
                )

            if ruta_archivo.stat().st_size <= 0:
                raise RuntimeError(
                    "CSV R2.2 vacio: "
                    f"{ruta_archivo}"
                )

            return {
                "ok": True,
                "unidad": unidad,
                "fecha": fecha,
                "ruta_archivo":
                    str(ruta_archivo),
                "bytes":
                    ruta_archivo.stat().st_size,
                "bridge":
                    self.bridge.name,
                "respuesta_bridge":
                    data,
            }

        finally:
            try:
                temporal_path.unlink(
                    missing_ok=True
                )
            except Exception:
                pass
