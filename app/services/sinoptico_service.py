from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class SinopticoServiceError(RuntimeError):
    pass


class SinopticoService:
    """
    Integracion SWAV -> SinopticoBridge.exe.

    El bridge recibe:
      stdin linea 1: usuario
      stdin linea 2: clave

    Y devuelve JSON por stdout.
    """

    def __init__(self) -> None:
        self._project_root = Path(__file__).resolve().parents[2]

        self._bridge_dir = (
            self._project_root
            / "backend"
            / "sinoptico_bridge"
        )

        self._bridge_exe = (
            self._bridge_dir
            / "SinopticoBridge.exe"
        )

        self._bridge_config = (
            self._bridge_dir
            / "SinopticoBridge.exe.config"
        )

        self._reportes_dll = (
            self._bridge_dir
            / "Reportes.dll"
        )

    def _validar_bridge(self) -> None:
        faltantes = []

        for ruta in (
            self._bridge_exe,
            self._bridge_config,
            self._reportes_dll,
        ):
            if not ruta.exists():
                faltantes.append(str(ruta))

        if faltantes:
            raise SinopticoServiceError(
                "Faltan archivos del bridge: "
                + " | ".join(faltantes)
            )

    def diagnostico(self) -> dict[str, Any]:
        self._validar_bridge()

        proceso = subprocess.run(
            [
                str(self._bridge_exe),
                "diagnostico",
            ],
            cwd=str(self._bridge_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )

        return self._procesar_resultado(
            proceso=proceso,
            operacion="diagnostico",
        )

    def login(
        self,
        usuario: str,
        clave: str,
    ) -> dict[str, Any]:
        self._validar_bridge()

        usuario = str(usuario or "").strip()
        clave = str(clave or "")

        if not usuario:
            raise SinopticoServiceError(
                "Usuario Sinoptico vacio."
            )

        if not clave:
            raise SinopticoServiceError(
                "Clave Sinoptico vacia."
            )

        entrada = (
            usuario
            + "\n"
            + clave
            + "\n"
        )

        try:
            proceso = subprocess.run(
                [
                    str(self._bridge_exe),
                    "loginhttp",
                ],
                cwd=str(self._bridge_dir),
                input=entrada,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=90,
                check=False,
            )

        finally:
            # No persistir intencionalmente la entrada.
            entrada = None
            clave = None

        resultado = self._procesar_resultado(
            proceso=proceso,
            operacion="loginhttp",
        )

        resultado["exit_code"] = (
            proceso.returncode
        )

        return resultado

    def _procesar_resultado(
        self,
        proceso: subprocess.CompletedProcess[str],
        operacion: str,
    ) -> dict[str, Any]:

        stdout = (
            proceso.stdout
            or ""
        ).strip()

        stderr = (
            proceso.stderr
            or ""
        ).strip()

        if not stdout:
            raise SinopticoServiceError(
                f"Bridge sin respuesta JSON. "
                f"Operacion={operacion}. "
                f"ExitCode={proceso.returncode}. "
                f"Stderr={stderr}"
            )

        try:
            data = json.loads(
                stdout
            )
        except json.JSONDecodeError as exc:
            raise SinopticoServiceError(
                "Respuesta JSON invalida del bridge. "
                f"Operacion={operacion}. "
                f"ExitCode={proceso.returncode}. "
                f"Stdout={stdout}. "
                f"Stderr={stderr}"
            ) from exc

        if not isinstance(data, dict):
            raise SinopticoServiceError(
                "El bridge no devolvio un objeto JSON."
            )

        # Nunca devolver prompts del bridge al frontend.
        # stderr solo se utiliza para diagnostico de errores.
        if (
            proceso.returncode != 0
            and data.get("ok") is not True
        ):
            data.setdefault(
                "error_bridge",
                stderr,
            )

        return data
