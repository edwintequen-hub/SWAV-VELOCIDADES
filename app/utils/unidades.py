"""
=========================================================
SWAV
Utilidades Unidad / Empresa
=========================================================
"""

# =========================================================
# MAPA OFICIAL SWAV
# =========================================================

MAPA_UNIDADES = {

    # ALFA
    "8": ("U8", "ALFA"),
    "U8": ("U8", "ALFA"),
    "ALFAU8": ("U8", "ALFA"),
    "ALFA": ("U8", "ALFA"),

    # OMEGA
    "9": ("U9", "OMEGA"),
    "U9": ("U9", "OMEGA"),
    "OMEGAU9": ("U9", "OMEGA"),
    "OMEGA": ("U9", "OMEGA"),

}


# =========================================================
# OBTENER UNIDAD Y EMPRESA
# =========================================================

def obtener_unidad_empresa(valor):

    if valor is None:

        return "", "DESCONOCIDA"

    valor = str(valor).strip().upper()

    # Cuando Excel entrega 8.0 o 9.0
    if valor.endswith(".0"):

        valor = valor[:-2]

    if valor not in MAPA_UNIDADES:

        raise ValueError(

            f"Unidad desconocida: {valor}"

        )

    return MAPA_UNIDADES[valor]