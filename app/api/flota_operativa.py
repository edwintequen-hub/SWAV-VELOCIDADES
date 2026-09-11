from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.flota_operativa_service import (
    consultar_detalle,
    consultar_flota,
    obtener_filtros,
)

router = APIRouter(prefix="/api/flota-operativa", tags=["Flota Operativa"])


@router.get("/filtros")
def filtros(db: Session = Depends(get_db)):
    return obtener_filtros(db)


@router.get("/consulta")
def consulta(
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
    unidad: str | None = Query(default=None),
    terminal: str | None = Query(default=None),
    servicio: str | None = Query(default=None),
    periodo_inicial: int = Query(default=1, ge=1, le=24),
    periodo_final: int = Query(default=24, ge=1, le=24),
    db: Session = Depends(get_db),
):
    try:
        return consultar_flota(
            db=db,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            unidad=unidad,
            terminal=terminal,
            servicio=servicio,
            periodo_inicial=periodo_inicial,
            periodo_final=periodo_final,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/detalle")
def detalle(
    fecha: str = Query(...),
    periodo: int = Query(..., ge=1, le=24),
    terminal: str = Query(...),
    servicio: str | None = Query(default=None),
    unidad: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        filas = consultar_detalle(
            db=db,
            fecha=fecha,
            periodo=periodo,
            terminal=terminal,
            servicio=servicio,
            unidad=unidad,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"total": len(filas), "registros": filas}

@router.get("/exportar-excel")
def exportar_excel(
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
    unidad: str | None = Query(default=None),
    terminal: str | None = Query(default=None),
    servicio: str | None = Query(default=None),
    periodo_inicial: int = Query(default=1, ge=1, le=24),
    periodo_final: int = Query(default=24, ge=1, le=24),
    db: Session = Depends(get_db),
):

    from io import BytesIO
    from collections import defaultdict

    from fastapi.responses import StreamingResponse

    from openpyxl import Workbook
    from openpyxl.chart import (
        BarChart,
        LineChart,
        DoughnutChart,
        Reference,
    )
    from openpyxl.styles import (
        Alignment,
        Font,
        PatternFill,
        Border,
        Side,
    )
    from openpyxl.utils import get_column_letter


    # ================================================================
    # HELPERS
    # ================================================================

    def periodo_txt(p):
        try:
            return f"P{int(p):02d}"
        except Exception:
            return str(p or "")


    def filtro_txt(valor, defecto="Todos"):
        if valor in (None, "", "null"):
            return defecto
        return str(valor)


    def estilizar_titulo(ws, titulo, subtitulo=None):

        ws.merge_cells("A1:H1")
        ws["A1"] = titulo
        ws["A1"].font = Font(
            bold=True,
            size=18,
            color="FFFFFF",
        )
        ws["A1"].fill = PatternFill(
            "solid",
            fgColor="1F4E78",
        )
        ws["A1"].alignment = Alignment(
            horizontal="center",
            vertical="center",
        )
        ws.row_dimensions[1].height = 28

        if subtitulo:
            ws.merge_cells("A2:H2")
            ws["A2"] = subtitulo
            ws["A2"].font = Font(
                italic=True,
                size=10,
                color="666666",
            )
            ws["A2"].alignment = Alignment(
                horizontal="center",
            )


    def preparar_tabla(ws):

        azul = PatternFill(
            "solid",
            fgColor="1F4E78",
        )

        borde = Border(
            bottom=Side(
                style="thin",
                color="D9E2F3",
            )
        )

        for cell in ws[1]:
            cell.font = Font(
                bold=True,
                color="FFFFFF",
            )
            cell.fill = azul
            cell.alignment = Alignment(
                horizontal="center",
            )

        for row in ws.iter_rows():

            for cell in row:

                cell.border = borde

        for col in range(
            1,
            ws.max_column + 1,
        ):

            ancho = 12

            for cell in ws[
                get_column_letter(col)
            ]:

                valor = str(
                    cell.value
                    if cell.value is not None
                    else ""
                )

                ancho = max(
                    ancho,
                    min(
                        len(valor) + 2,
                        32,
                    )
                )

            ws.column_dimensions[
                get_column_letter(col)
            ].width = ancho


    def crear_dashboard(
        wb,
        nombre_hoja,
        titulo,
        datos,
        empresa=None,
    ):

        total = (
            datos.get("total_global")
            or {}
        )

        resumen_terminal_global = (
            datos.get("resumen_terminal_global")
            or []
        )

        resumen_terminal = (
            datos.get("resumen_terminal")
            or []
        )

        cobertura = (
            datos.get("cobertura_fuente")
            or []
        )

        ws = wb.create_sheet(
            nombre_hoja
        )

        estilizar_titulo(
            ws,
            titulo,
            (
                f"Per\u00edodo {periodo_txt(periodo_inicial)} "
                f"a {periodo_txt(periodo_final)}"
            ),
        )

        # ------------------------------------------------------------
        # FILTROS
        # ------------------------------------------------------------

        ws["A4"] = "Fecha desde"
        ws["B4"] = filtro_txt(fecha_desde, "-")

        ws["A5"] = "Fecha hasta"
        ws["B5"] = filtro_txt(fecha_hasta, "-")

        ws["A6"] = "Unidad"
        ws["B6"] = (
            empresa
            if empresa
            else filtro_txt(unidad, "Todas")
        )

        ws["A7"] = "Terminal"
        ws["B7"] = filtro_txt(
            terminal,
            "Todos",
        )

        ws["A8"] = "Servicio"
        ws["B8"] = filtro_txt(
            servicio,
            "Todos",
        )

        # ------------------------------------------------------------
        # KPIs
        # ------------------------------------------------------------

        kpis = [
            (
                "Flota asignada",
                int(
                    total.get("asignada")
                    or 0
                ),
            ),
            (
                "Buses en la calle",
                int(
                    total.get("operativa")
                    or 0
                ),
            ),
            (
                "Sin transmisi\u00f3n",
                int(
                    total.get("sin_transmision")
                    or 0
                ),
            ),
            (
                "% Operativa",
                float(
                    total.get("porcentaje_operativa")
                    or 0
                ) / 100,
            ),
        ]

        fila_kpi = 4

        for titulo_kpi, valor in kpis:

            ws.cell(
                fila_kpi,
                4,
                titulo_kpi,
            )

            ws.cell(
                fila_kpi,
                5,
                valor,
            )

            ws.cell(
                fila_kpi,
                4,
            ).font = Font(
                bold=True,
                color="FFFFFF",
            )

            ws.cell(
                fila_kpi,
                4,
            ).fill = PatternFill(
                "solid",
                fgColor="4472C4",
            )

            ws.cell(
                fila_kpi,
                5,
            ).font = Font(
                bold=True,
                size=14,
            )

            fila_kpi += 1

        ws["E7"].number_format = "0.00%"

        # ------------------------------------------------------------
        # COBERTURA / D?A PARCIAL
        # ------------------------------------------------------------

        parciales = [
            c
            for c in cobertura
            if not bool(
                c.get("dia_completo")
            )
        ]

        if parciales:

            ws.merge_cells(
                "A10:H10"
            )

            ws["A10"] = (
                "ADVERTENCIA: "
                "R1.6 DEL D?A ACTUAL ES PARCIAL"
            )

            ws["A10"].font = Font(
                bold=True,
                color="9C6500",
            )

            ws["A10"].fill = PatternFill(
                "solid",
                fgColor="FFEB9C",
            )

            ws["A10"].alignment = Alignment(
                horizontal="center",
            )

        # ------------------------------------------------------------
        # TABLA TERMINALES
        # ------------------------------------------------------------

        fila_tabla = 13

        encabezados = [
            "Terminal",
            "Asignada",
            "En calle",
            "Sin Tx",
            "% Operativa",
        ]

        for col, h in enumerate(
            encabezados,
            start=1,
        ):
            c = ws.cell(
                fila_tabla,
                col,
                h,
            )

            c.font = Font(
                bold=True,
                color="FFFFFF",
            )

            c.fill = PatternFill(
                "solid",
                fgColor="1F4E78",
            )

        fila = fila_tabla + 1

        for r in resumen_terminal_global:

            ws.cell(
                fila,
                1,
                r.get("terminal_nombre")
                or r.get("terminal")
                or "",
            )

            ws.cell(
                fila,
                2,
                int(
                    r.get("asignada")
                    or 0
                ),
            )

            ws.cell(
                fila,
                3,
                int(
                    r.get("operativa")
                    or 0
                ),
            )

            ws.cell(
                fila,
                4,
                int(
                    r.get("sin_transmision")
                    or 0
                ),
            )

            ws.cell(
                fila,
                5,
                float(
                    r.get("porcentaje_operativa")
                    or 0
                ) / 100,
            )

            ws.cell(
                fila,
                5,
            ).number_format = "0.00%"

            fila += 1

        # ------------------------------------------------------------
        # GR?FICO BARRAS
        # ------------------------------------------------------------

        if fila > fila_tabla + 1:

            chart = BarChart()

            chart.type = "col"
            chart.style = 10

            chart.title = (
                "Flota asignada vs "
                "Buses en la calle por terminal"
            )

            chart.y_axis.title = "Buses"
            chart.x_axis.title = "Terminal"

            chart.height = 8
            chart.width = 16

            chart.legend.position = "b"

            datos_chart = Reference(
                ws,
                min_col=2,
                max_col=3,
                min_row=fila_tabla,
                max_row=fila - 1,
            )

            categorias = Reference(
                ws,
                min_col=1,
                min_row=fila_tabla + 1,
                max_row=fila - 1,
            )

            chart.add_data(
                datos_chart,
                titles_from_data=True,
            )

            chart.set_categories(
                categorias
            )

            ws.add_chart(
                chart,
                "G13",
            )

        # ------------------------------------------------------------
        # DONA ESTADO GENERAL
        # ------------------------------------------------------------

        ws["N4"] = "Estado"
        ws["O4"] = "Cantidad"

        ws["N5"] = "Buses en la calle"
        ws["O5"] = int(
            total.get("operativa")
            or 0
        )

        ws["N6"] = "Sin transmisi\u00f3n"
        ws["O6"] = int(
            total.get("sin_transmision")
            or 0
        )

        dona = DoughnutChart()

        dona.title = (
            "Estado general de la flota"
        )

        datos_dona = Reference(
            ws,
            min_col=15,
            min_row=4,
            max_row=6,
        )

        categorias_dona = Reference(
            ws,
            min_col=14,
            min_row=5,
            max_row=6,
        )

        dona.add_data(
            datos_dona,
            titles_from_data=True,
        )

        dona.set_categories(
            categorias_dona
        )

        dona.holeSize = 62
        dona.firstSliceAng = 270
        dona.height = 8
        dona.width = 10
        dona.legend.position = "b"

        ws.add_chart(
            dona,
            "W13",
        )

        # ------------------------------------------------------------
        # COMPORTAMIENTO P01-P24
        # ------------------------------------------------------------

        comportamiento = defaultdict(int)

        for r in resumen_terminal:

            p = r.get("periodo")

            if p is None:
                continue

            comportamiento[
                int(p)
            ] += int(
                r.get("operativa")
                or 0
            )

        fila_periodo = 32

        ws.cell(
            fila_periodo,
            1,
            "Per\u00edodo",
        )

        ws.cell(
            fila_periodo,
            2,
            "Flota operativa",
        )

        for c in (
            ws.cell(fila_periodo, 1),
            ws.cell(fila_periodo, 2),
        ):
            c.font = Font(
                bold=True,
                color="FFFFFF",
            )

            c.fill = PatternFill(
                "solid",
                fgColor="1F4E78",
            )

        fila_p = fila_periodo + 1

        for p in range(
            int(periodo_inicial),
            int(periodo_final) + 1,
        ):

            ws.cell(
                fila_p,
                1,
                periodo_txt(p),
            )

            ws.cell(
                fila_p,
                2,
                comportamiento.get(
                    p,
                    0,
                ),
            )

            fila_p += 1

        linea = LineChart()

        linea.title = (
            "Comportamiento de la flota P01-P24"
        )

        linea.style = 13
        linea.height = 8
        linea.width = 18

        linea.y_axis.title = (
            "Flota operativa"
        )

        linea.x_axis.title = (
            "Per\u00edodo"
        )

        linea.legend.position = "b"

        data = Reference(
            ws,
            min_col=2,
            min_row=fila_periodo,
            max_row=fila_p - 1,
        )

        cats = Reference(
            ws,
            min_col=1,
            min_row=fila_periodo + 1,
            max_row=fila_p - 1,
        )

        linea.add_data(
            data,
            titles_from_data=True,
        )

        linea.set_categories(
            cats
        )

        for serie in linea.series:

            serie.marker.symbol = "circle"
            serie.marker.size = 6

        ws.add_chart(
            linea,
            "G32",
        )

        # ------------------------------------------------------------
        # COLUMN WIDTHS
        # ------------------------------------------------------------

        for col, ancho in {
            "A": 22,
            "B": 16,
            "C": 14,
            "D": 18,
            "E": 16,
            "F": 4,
        }.items():

            ws.column_dimensions[
                col
            ].width = ancho

        ws.freeze_panes = "A13"

        return ws


    # ================================================================
    # CONSULTAS
    # ================================================================

    datos_general = consultar_flota(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        unidad=unidad,
        terminal=terminal,
        servicio=servicio,
        periodo_inicial=periodo_inicial,
        periodo_final=periodo_final,
    )

    datos_u8 = consultar_flota(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        unidad="U8",
        terminal=terminal,
        servicio=servicio,
        periodo_inicial=periodo_inicial,
        periodo_final=periodo_final,
    )

    datos_u9 = consultar_flota(
        db=db,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        unidad="U9",
        terminal=terminal,
        servicio=servicio,
        periodo_inicial=periodo_inicial,
        periodo_final=periodo_final,
    )


    # ================================================================
    # R10 - HISTORICO DIARIO REAL
    # ================================================================

    from datetime import datetime, timedelta

    historico = {
        "U8": [],
        "U9": [],
    }

    fecha_hist_desde = fecha_desde
    fecha_hist_hasta = fecha_hasta

    if fecha_hist_desde and fecha_hist_hasta:

        f_ini = datetime.strptime(
            fecha_hist_desde,
            "%Y-%m-%d",
        ).date()

        f_fin = datetime.strptime(
            fecha_hist_hasta,
            "%Y-%m-%d",
        ).date()

        fecha_cursor = f_ini

        while fecha_cursor <= f_fin:

            fecha_txt = fecha_cursor.strftime(
                "%Y-%m-%d"
            )

            for unidad_hist in ("U8", "U9"):

                datos_dia = consultar_flota(
                    db=db,
                    fecha_desde=fecha_txt,
                    fecha_hasta=fecha_txt,
                    unidad=unidad_hist,
                    terminal=terminal,
                    servicio=servicio,
                    periodo_inicial=periodo_inicial,
                    periodo_final=periodo_final,
                )

                historico[
                    unidad_hist
                ].append({
                    "fecha": fecha_txt,
                    "datos": datos_dia,
                })

            fecha_cursor += timedelta(days=1)


    # ================================================================
    # HELPERS R10
    # ================================================================

    EMPRESA_UNIDAD = {
        "U8": "ALFA",
        "U9": "OMEGA",
    }


    def nombre_terminal(r):

        return (
            r.get("terminal_nombre")
            or r.get("terminal")
            or ""
        )


    def serie_periodos_terminal(datos):

        salida = defaultdict(
            lambda: defaultdict(int)
        )

        for r in (
            datos.get("resumen_terminal")
            or []
        ):

            p = r.get("periodo")

            if p is None:
                continue

            terminal_r = nombre_terminal(r)

            salida[
                terminal_r
            ][int(p)] += int(
                r.get("operativa")
                or 0
            )

        return salida


    def crear_resumen_historico(
        wb,
        unidad_nombre,
    ):

        empresa = EMPRESA_UNIDAD[
            unidad_nombre
        ]

        ws = wb.create_sheet(
            f"Resumen {unidad_nombre}"
        )

        ws.append([
            "Fecha",
            "Unidad",
            "Empresa",
            "Flota asignada",
            "Buses en la calle",
            "Sin transmisi\u00f3n",
            "% Operativa",
            "Cobertura",
        ])

        for item in historico[
            unidad_nombre
        ]:

            fecha_r = item["fecha"]
            datos_r = item["datos"]

            total = (
                datos_r.get("total_global")
                or {}
            )

            cobertura = (
                datos_r.get(
                    "cobertura_fuente"
                )
                or []
            )

            estado_cobertura = "COMPLETO"

            for c in cobertura:

                if not bool(
                    c.get("dia_completo")
                ):
                    estado_cobertura = (
                        "PARCIAL HASTA "
                        + str(
                            c.get("hasta")
                            or ""
                        )
                    )

            ws.append([
                fecha_r,
                unidad_nombre,
                empresa,
                int(
                    total.get("asignada")
                    or 0
                ),
                int(
                    total.get("operativa")
                    or 0
                ),
                int(
                    total.get(
                        "sin_transmision"
                    )
                    or 0
                ),
                float(
                    total.get(
                        "porcentaje_operativa"
                    )
                    or 0
                ) / 100,
                estado_cobertura,
            ])

        preparar_tabla(ws)

        for fila in range(
            2,
            ws.max_row + 1,
        ):
            ws.cell(
                fila,
                7,
            ).number_format = "0.00%"

        ws.freeze_panes = "A2"

        return ws


    def crear_comportamiento(
        wb,
        unidad_nombre,
        datos_unidad,
    ):

        empresa = EMPRESA_UNIDAD[
            unidad_nombre
        ]

        ws = wb.create_sheet(
            f"Comportamiento {unidad_nombre}"
        )

        serie_terminal = (
            serie_periodos_terminal(
                datos_unidad
            )
        )

        terminales = sorted(
            serie_terminal.keys()
        )

        ws.append(
            ["Per\u00edodo"]
            + terminales
            + [f"TOTAL {unidad_nombre}"]
        )

        for p in range(
            int(periodo_inicial),
            int(periodo_final) + 1,
        ):

            valores = [
                serie_terminal[t].get(
                    p,
                    0,
                )
                for t in terminales
            ]

            ws.append(
                [periodo_txt(p)]
                + valores
                + [sum(valores)]
            )

        preparar_tabla(ws)

        ws.freeze_panes = "A2"

        if ws.max_row >= 2:

            chart = LineChart()

            chart.title = (
                "Comportamiento de la flota "
                f"{unidad_nombre} - {empresa} "
                "por per\u00edodo"
            )

            chart.style = 13
            chart.height = 12
            chart.width = 23

            chart.y_axis.title = (
                "Buses operativos"
            )

            chart.x_axis.title = (
                "Per\u00edodo"
            )

            data = Reference(
                ws,
                min_col=2,
                max_col=ws.max_column,
                min_row=1,
                max_row=ws.max_row,
            )

            cats = Reference(
                ws,
                min_col=1,
                min_row=2,
                max_row=ws.max_row,
            )

            chart.add_data(
                data,
                titles_from_data=True,
            )

            chart.set_categories(
                cats
            )

            chart.legend.position = "r"

            for serie in chart.series:
                serie.marker.symbol = (
                    "circle"
                )
                serie.marker.size = 5

            ws.add_chart(
                chart,
                "A29",
            )

        return ws


    def crear_sin_tx_historico(
        wb,
        unidad_nombre,
    ):

        empresa = EMPRESA_UNIDAD[
            unidad_nombre
        ]

        ws = wb.create_sheet(
            f"Sin Tx Hist\u00f3rico {unidad_nombre}"
        )

        terminales = []

        for item in historico[
            unidad_nombre
        ]:

            for r in (
                item["datos"].get(
                    "resumen_terminal_global"
                )
                or []
            ):

                t = nombre_terminal(r)

                if (
                    t
                    and t not in terminales
                ):
                    terminales.append(t)

        terminales.sort()

        # ------------------------------------------------------------
        # MATRIZ HISTORICA PARA GRAFICO
        # ------------------------------------------------------------

        ws.append(
            ["Fecha"]
            + terminales
            + [f"TOTAL {unidad_nombre}"]
        )

        fila_matriz_inicio = 2

        for item in historico[
            unidad_nombre
        ]:

            por_terminal = {}

            for r in (
                item["datos"].get(
                    "resumen_terminal_global"
                )
                or []
            ):

                por_terminal[
                    nombre_terminal(r)
                ] = int(
                    r.get(
                        "sin_transmision"
                    )
                    or 0
                )

            valores = [
                por_terminal.get(
                    t,
                    0,
                )
                for t in terminales
            ]

            ws.append(
                [item["fecha"]]
                + valores
                + [sum(valores)]
            )

        fila_matriz_fin = ws.max_row

        preparar_tabla(ws)

        ws.freeze_panes = "A2"

        # ------------------------------------------------------------
        # GRAFICO DE SERIES HISTORICAS
        # ------------------------------------------------------------

        if fila_matriz_fin >= 2:

            chart = LineChart()

            chart.title = (
                "PPU sin transmisi\u00f3n por d\u00eda "
                f"y terminal - {unidad_nombre} "
                f"{empresa}"
            )

            chart.style = 13
            chart.height = 13
            chart.width = 25

            chart.y_axis.title = (
                "PPU sin transmisi\u00f3n"
            )

            chart.x_axis.title = "Fecha"

            data = Reference(
                ws,
                min_col=2,
                max_col=ws.max_column,
                min_row=1,
                max_row=fila_matriz_fin,
            )

            cats = Reference(
                ws,
                min_col=1,
                min_row=2,
                max_row=fila_matriz_fin,
            )

            chart.add_data(
                data,
                titles_from_data=True,
            )

            chart.set_categories(
                cats
            )

            chart.legend.position = "r"

            for serie in chart.series:
                serie.marker.symbol = (
                    "circle"
                )
                serie.marker.size = 6

            ws.add_chart(
                chart,
                "A8",
            )


        # ------------------------------------------------------------
        # DETALLE PPU SIN TRANSMISION POR FECHA
        # ------------------------------------------------------------

        fila_detalle = max(
            fila_matriz_fin + 20,
            30,
        )

        headers_detalle = [
            "Fecha",
            "Unidad",
            "Empresa",
            "Terminal",
            "PPU",
            "Interno",
            "Tipo Bus",
            "Tipo Flota",
            "Estado",
        ]

        for col, valor in enumerate(
            headers_detalle,
            start=1,
        ):

            cell = ws.cell(
                fila_detalle,
                col,
                valor,
            )

            cell.font = Font(
                bold=True,
                color="FFFFFF",
            )

            cell.fill = PatternFill(
                "solid",
                fgColor="1F4E78",
            )

            cell.alignment = Alignment(
                horizontal="center",
            )

        fila = fila_detalle + 1

        for item in historico[
            unidad_nombre
        ]:

            fecha_r = item["fecha"]

            for r in (
                item["datos"].get(
                    "sin_transmision_detalle"
                )
                or []
            ):

                ws.cell(
                    fila,
                    1,
                    fecha_r,
                )

                ws.cell(
                    fila,
                    2,
                    unidad_nombre,
                )

                ws.cell(
                    fila,
                    3,
                    empresa,
                )

                ws.cell(
                    fila,
                    4,
                    nombre_terminal(r),
                )

                ws.cell(
                    fila,
                    5,
                    r.get("ppu"),
                )

                ws.cell(
                    fila,
                    6,
                    r.get("interno"),
                )

                ws.cell(
                    fila,
                    7,
                    r.get("tipo_bus"),
                )

                ws.cell(
                    fila,
                    8,
                    r.get("tipo_flota"),
                )

                ws.cell(
                    fila,
                    9,
                    r.get("estado"),
                )

                fila += 1

        for col in range(
            1,
            10,
        ):

            ws.column_dimensions[
                get_column_letter(col)
            ].width = 20

        ws.column_dimensions["A"].width = 14
        ws.column_dimensions["D"].width = 22
        ws.column_dimensions["E"].width = 14

        return ws


    # ================================================================
    # WORKBOOK R10
    # ================================================================

    wb = Workbook()

    hoja_default = wb.active
    wb.remove(hoja_default)


    # ================================================================
    # 01 DASHBOARD U8 - ALFA
    # ================================================================

    crear_dashboard(
        wb,
        "Dashboard U8 - ALFA",
        "SWAV - FLOTA OPERATIVA - U8 ALFA",
        datos_u8,
        "U8 - ALFA",
    )


    # ================================================================
    # 02 RESUMEN U8
    # ================================================================

    crear_resumen_historico(
        wb,
        "U8",
    )


    # ================================================================
    # 03 COMPORTAMIENTO U8
    # ================================================================

    crear_comportamiento(
        wb,
        "U8",
        datos_u8,
    )


    # ================================================================
    # 04 SIN TX HISTORICO U8
    # ================================================================

    crear_sin_tx_historico(
        wb,
        "U8",
    )


    # ================================================================
    # 05 DASHBOARD U9 - OMEGA
    # ================================================================

    crear_dashboard(
        wb,
        "Dashboard U9 - OMEGA",
        "SWAV - FLOTA OPERATIVA - U9 OMEGA",
        datos_u9,
        "U9 - OMEGA",
    )


    # ================================================================
    # 06 RESUMEN U9
    # ================================================================

    crear_resumen_historico(
        wb,
        "U9",
    )


    # ================================================================
    # 07 COMPORTAMIENTO U9
    # ================================================================

    crear_comportamiento(
        wb,
        "U9",
        datos_u9,
    )


    # ================================================================
    # 08 SIN TX HISTORICO U9
    # ================================================================

    crear_sin_tx_historico(
        wb,
        "U9",
    )


    # ================================================================
    # COBERTURA R1.6
    # Se mantiene como hoja tecnica adicional.
    # ================================================================

    ws_c = wb.create_sheet(
        "Cobertura R1.6"
    )

    ws_c.append([
        "Unidad",
        "Fecha",
        "Hasta",
        "Archivo",
        "D\u00eda completo",
    ])

    cobertura_general = (
        datos_general.get(
            "cobertura_fuente"
        )
        or []
    )

    for r in cobertura_general:

        ws_c.append([
            r.get("unidad"),
            r.get("fecha"),
            r.get("hasta"),
            r.get("archivo"),
            r.get("dia_completo"),
        ])

    preparar_tabla(ws_c)


    # ================================================================
    # SALIDA
    # ================================================================

    buffer = BytesIO()

    wb.save(
        buffer
    )

    buffer.seek(0)

    desde_nombre = (
        fecha_desde
        or "inicio"
    )

    hasta_nombre = (
        fecha_hasta
        or "fin"
    )

    nombre_archivo = (
        f"SWAV_FLOTA_OPERATIVA_"
        f"{desde_nombre}_"
        f"{hasta_nombre}.xlsx"
    )

    headers = {
        "Content-Disposition":
            f'attachment; filename="{nombre_archivo}"'
    }

    return StreamingResponse(
        buffer,
        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers=headers,
    )
