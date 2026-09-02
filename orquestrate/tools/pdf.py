"""
Módulo de generación de PDFs comparativos - Grupo Núcleo.

Diseño:
    - A4 horizontal
    - Margen superior: 0 mm
    - Margen izquierdo: 0 mm
    - Margen derecho: 0 mm
    - Margen inferior: 18 mm
    - Frame interno sin padding
    - Encabezado institucional
    - Bloque de consulta
    - Resumen de resultados
    - Tabla de productos
    - Pie de página
"""

import os
import time
import logging
import re
import hashlib
import requests


# ==========================================================================
# PARCHE MD5 / REPORTLAB
# ==========================================================================

_original_md5 = hashlib.md5


def _safe_md5(*args, **kwargs):
    kwargs.pop("usedforsecurity", None)
    return _original_md5(*args, **kwargs)


hashlib.md5 = _safe_md5


# ==========================================================================
# REPORTLAB
# ==========================================================================

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors

from reportlab.platypus import (
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)

from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle,
)


# ==========================================================================
# CONFIGURACIÓN
# ==========================================================================

log = logging.getLogger("asistente")

PDF_FOLDER = "pdf_generados"

# Ruta absoluta al directorio raíz del proyecto
# (directorio padre de tools/)
_BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

LOGO_URL = (
    "https://raw.githubusercontent.com/Cecchi08/Jetson/"
    "main/assets/Logo_Nucleo_rojo-blanco.png"
)

LOGO_LOCAL_PATH = os.path.join(
    _BASE_DIR,
    "assets",
    "Logo_Nucleo_rojo-blanco.png"
)


# ==========================================================================
# COLORES
# =========================================================================:

AZUL_NUCLEO = colors.HexColor("#101828")
AZUL_OSCURO = colors.HexColor("#0B1220")

ROJO_NUCLEO = colors.HexColor("#D7193F")

BLANCO = colors.white

GRIS_900 = colors.HexColor("#1D2939")
GRIS_700 = colors.HexColor("#475467")
GRIS_600 = colors.HexColor("#667085")
GRIS_500 = colors.HexColor("#98A2B3")

GRIS_300 = colors.HexColor("#D0D5DD")
GRIS_200 = colors.HexColor("#EAECF0")
GRIS_100 = colors.HexColor("#F2F4F7")
GRIS_50 = colors.HexColor("#F9FAFB")

VERDE_STOCK = colors.HexColor("#027A48")
VERDE_FONDO = colors.HexColor("#ECFDF3")

ROJO_STOCK = colors.HexColor("#B42318")
ROJO_FONDO = colors.HexColor("#FEF3F2")


# ==========================================================================
# UTILIDADES
# ==========================================================================

def normalizar_nombre_pdf(texto):
    """
    Normaliza el nombre del archivo PDF.
    """

    from .catalogo import normalizar

    nombre = normalizar(texto)

    nombre = re.sub(
        r"[^a-z0-9]+",
        "_",
        nombre
    )

    nombre = nombre.strip("_")

    return nombre if nombre else "productos"


def _obtener_logo():
    """
    Obtiene el logo desde el cache local.

    Si no existe, intenta descargarlo.

    Si la descarga falla, el PDF se genera
    igualmente sin logo.
    """

    if os.path.exists(LOGO_LOCAL_PATH):
        return LOGO_LOCAL_PATH

    try:

        respuesta = requests.get(
            LOGO_URL,
            timeout=10
        )

        respuesta.raise_for_status()

        with open(
            LOGO_LOCAL_PATH,
            "wb"
        ) as archivo:

            archivo.write(
                respuesta.content
            )

        return LOGO_LOCAL_PATH

    except Exception as e:

        log.warning(
            "No se pudo descargar el logo: %s",
            e
        )

        return None


def _escape(texto):
    """
    Escapa caracteres especiales para Paragraph.
    """

    if texto is None:
        return ""

    texto = str(texto)

    texto = texto.replace(
        "&",
        "&amp;"
    )

    texto = texto.replace(
        "<",
        "&lt;"
    )

    texto = texto.replace(
        ">",
        "&gt;"
    )

    return texto


def _stock_entero(valor):
    """
    Convierte un valor de stock a entero.
    """

    try:

        return int(
            float(valor)
        )

    except (
        TypeError,
        ValueError
    ):

        return 0


def _precio(valor):
    """
    Formatea un precio en USD.
    """

    try:

        valor = float(valor)

        return f"USD {valor:,.2f}"

    except (
        TypeError,
        ValueError
    ):

        return "USD 0.00"


def _obtener_descripcion(producto):
    """
    Obtiene la descripción del producto.
    """

    return (
        producto.get("nombre")
        or producto.get("descripcion")
        or "Sin descripción"
    )


# ==========================================================================
# GENERADOR
# ==========================================================================

def generar_pdf_productos(
    productos,
    consulta,
    cotizacion=None
):
    """
    Genera un PDF comercial de productos.

    Márgenes físicos:

        Superior: 0 mm
        Izquierdo: 0 mm
        Derecho: 0 mm
        Inferior: 18 mm

    Además, el Frame de ReportLab utiliza padding 0 en
    los cuatro lados para evitar el margen interno
    predeterminado de 6 puntos.

    Parámetros:
        productos:
            Lista de diccionarios de productos.

        consulta:
            Texto utilizado para realizar la búsqueda.

        cotizacion:
            Cotización del dólar GN.

    Retorna:
        str | None:
            Ruta absoluta del PDF generado.
    """

    try:

        # ==================================================================
        # CARPETA
        # ==================================================================

        os.makedirs(
            PDF_FOLDER,
            exist_ok=True
        )

        # ==================================================================
        # NOMBRE DEL ARCHIVO
        # ==================================================================

        nombre = normalizar_nombre_pdf(
            consulta
        )

        timestamp = time.strftime(
            "%Y%m%d_%H%M%S"
        )

        ruta = os.path.abspath(
            os.path.join(
                PDF_FOLDER,
                f"{nombre}_{timestamp}.pdf"
            )
        )

        # ==================================================================
        # TAMAÑO DE PÁGINA
        # ==================================================================

        pagina = landscape(A4)

        ancho_pagina = pagina[0]
        alto_pagina = pagina[1]

        # ==================================================================
        # MARGEN INFERIOR
        # ==================================================================

        margen_inferior = 18 * mm

        # ==================================================================
        # FRAME
        #
        # ESTA ES LA PARTE IMPORTANTE.
        #
        # ReportLab utiliza 6 puntos de padding interno
        # por defecto en Frame.
        #
        # Por eso aunque leftMargin/topMargin sean 0,
        # el contenido podía empezar varios píxeles
        # separado del borde.
        #
        # Ahora todos los paddings son 0.
        # ==================================================================

        frame = Frame(

            0,

            margen_inferior,

            ancho_pagina,

            alto_pagina - margen_inferior,

            leftPadding=0,

            rightPadding=0,

            topPadding=0,

            bottomPadding=0,

            id="contenido",

            showBoundary=0,
        )

        # ==================================================================
        # CALLBACK DEL FOOTER
        # ==================================================================

        def _pie_pagina(
            canvas,
            documento
        ):

            canvas.saveState()

            # --------------------------------------------------------------
            # Línea superior del footer
            # --------------------------------------------------------------

            canvas.setStrokeColor(
                GRIS_200
            )

            canvas.setLineWidth(
                0.5
            )

            canvas.line(

                0,

                9 * mm,

                ancho_pagina,

                9 * mm
            )

            # --------------------------------------------------------------
            # Texto izquierdo
            # --------------------------------------------------------------

            canvas.setFont(
                "Helvetica",
                6.8
            )

            canvas.setFillColor(
                GRIS_500
            )

            canvas.drawString(

                10 * mm,

                5 * mm,

                "Grupo Núcleo · Lista de productos"
            )

            # --------------------------------------------------------------
            # Número de página
            # --------------------------------------------------------------

            canvas.drawRightString(

                ancho_pagina - 10 * mm,

                5 * mm,

                f"Página {documento.page}"
            )

            canvas.restoreState()

        # ==================================================================
        # DOCUMENTO
        #
        # No utilizamos SimpleDocTemplate porque queremos controlar
        # directamente el Frame.
        # ==================================================================

        doc = BaseDocTemplate(

            ruta,

            pagesize=pagina,

            leftMargin=0,

            rightMargin=0,

            topMargin=0,

            bottomMargin=margen_inferior,

            title="Lista de productos - Grupo Núcleo",

            author="Grupo Núcleo",
        )

        # ==================================================================
        # PAGE TEMPLATE
        # ==================================================================

        template = PageTemplate(

            id="principal",

            frames=[frame],

            onPage=_pie_pagina,
        )

        doc.addPageTemplates(
            [template]
        )

        # ==================================================================
        # ANCHO ÚTIL
        #
        # Ahora es exactamente el ancho físico de A4.
        # ==================================================================

        ancho_util = ancho_pagina

        # ==================================================================
        # ESTILOS
        # ==================================================================

        estilos = getSampleStyleSheet()

        # ------------------------------------------------------------------
        # TÍTULO
        # ------------------------------------------------------------------

        estilo_titulo = ParagraphStyle(

            "TituloNucleo",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=18,

            leading=21,

            textColor=BLANCO,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # SUBTÍTULO
        # ------------------------------------------------------------------

        estilo_subtitulo = ParagraphStyle(

            "SubtituloNucleo",

            parent=estilos["Normal"],

            fontName="Helvetica",

            fontSize=8.5,

            leading=10,

            textColor=colors.HexColor(
                "#D0D5DD"
            ),

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # LABEL
        # ------------------------------------------------------------------

        estilo_label = ParagraphStyle(

            "Label",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=7,

            leading=8,

            textColor=GRIS_600,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # CONSULTA
        # ------------------------------------------------------------------

        estilo_consulta = ParagraphStyle(

            "Consulta",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=11,

            leading=13,

            textColor=GRIS_900,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # RESUMEN
        # ------------------------------------------------------------------

        estilo_resumen_numero = ParagraphStyle(

            "ResumenNumero",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=12,

            leading=13,

            textColor=GRIS_900,

            alignment=1,

            spaceAfter=0,
        )

        estilo_resumen_label = ParagraphStyle(

            "ResumenLabel",

            parent=estilos["Normal"],

            fontName="Helvetica",

            fontSize=6.8,

            leading=8,

            textColor=GRIS_600,

            alignment=1,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # HEADER TABLA
        # ------------------------------------------------------------------

        estilo_header = ParagraphStyle(

            "HeaderTabla",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=7.3,

            leading=8.5,

            textColor=BLANCO,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # CÓDIGO
        # ------------------------------------------------------------------

        estilo_codigo = ParagraphStyle(

            "Codigo",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=8,

            leading=9.5,

            textColor=GRIS_700,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # DESCRIPCIÓN
        # ------------------------------------------------------------------

        estilo_descripcion = ParagraphStyle(

            "Descripcion",

            parent=estilos["Normal"],

            fontName="Helvetica",

            fontSize=8,

            leading=10,

            textColor=GRIS_900,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # PRECIO
        # ------------------------------------------------------------------

        estilo_precio = ParagraphStyle(

            "Precio",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=8.2,

            leading=10,

            alignment=2,

            textColor=GRIS_900,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # STOCK
        # ------------------------------------------------------------------

        estilo_stock = ParagraphStyle(

            "Stock",

            parent=estilos["Normal"],

            fontName="Helvetica",

            fontSize=8.2,

            leading=10,

            alignment=1,

            textColor=GRIS_700,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # STOCK TOTAL
        # ------------------------------------------------------------------

        estilo_stock_total = ParagraphStyle(

            "StockTotal",

            parent=estilos["Normal"],

            fontName="Helvetica-Bold",

            fontSize=8.5,

            leading=10,

            alignment=1,

            textColor=VERDE_STOCK,

            spaceAfter=0,
        )

        # ------------------------------------------------------------------
        # FOOTER
        # ------------------------------------------------------------------

        estilo_footer = ParagraphStyle(

            "Footer",

            parent=estilos["Normal"],

            fontName="Helvetica",

            fontSize=6.8,

            leading=8,

            textColor=GRIS_500,

            spaceAfter=0,
        )

        # ==================================================================
        # COTIZACIÓN
        # ==================================================================

        if cotizacion:

            try:

                valor_dolar = float(
                    cotizacion
                )

                texto_dolar = (
                    f"Dólar GN "
                    f"${valor_dolar:,.0f}"
                )

            except (
                TypeError,
                ValueError
            ):

                texto_dolar = (
                    "Dólar GN no disponible"
                )

        else:

            texto_dolar = (
                "Dólar GN no disponible"
            )

        # ==================================================================
        # RESUMEN
        # ==================================================================

        cantidad_productos = len(
            productos
        )

        stock_general = 0

        for producto in productos:

            stock_general += (
                _stock_entero(
                    producto.get(
                        "stock_mdp",
                        0
                    )
                )
                +
                _stock_entero(
                    producto.get(
                        "stock_caba",
                        0
                    )
                )
            )

        # ==================================================================
        # ELEMENTOS
        # ==================================================================

        elementos = []

        # ==================================================================
        # HEADER
        # ==================================================================

        logo_path = _obtener_logo()

        fecha = time.strftime(
            "%d/%m/%Y"
        )

        hora = time.strftime(
            "%H:%M:%S"
        )

        bloque_header = [

            Paragraph(
                "Lista de productos",
                estilo_titulo
            ),

            Spacer(
                1,
                1.2 * mm
            ),

            Paragraph(
                "Grupo Núcleo",
                estilo_subtitulo
            ),

            Spacer(
                1,
                1.8 * mm
            ),

            Paragraph(
                (
                    f"Emitido: {fecha} · {hora}"
                    f"  |  "
                    f"{_escape(texto_dolar)}"
                ),
                estilo_subtitulo
            ),
        ]

        if logo_path:

            logo = Image(

                logo_path,

                width=39 * mm,

                height=14 * mm,

                hAlign="LEFT",
            )

            header = Table(

                [
                    [
                        logo,
                        bloque_header
                    ]
                ],

                colWidths=[
                    58 * mm,
                    ancho_util - 58 * mm
                ],

                hAlign="LEFT",
            )

        else:

            header = Table(

                [
                    [
                        bloque_header
                    ]
                ],

                colWidths=[
                    ancho_util
                ],

                hAlign="LEFT",
            )

        header.setStyle(

            TableStyle(
                [

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        AZUL_NUCLEO
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),

                    # ------------------------------------------------------
                    # PADDING INTERNO
                    #
                    # Este padding NO es margen de página.
                    # Solo separa el contenido del borde azul.
                    # ------------------------------------------------------

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        15
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        15
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        9
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        9
                    ),
                ]
            )
        )

        elementos.append(
            header
        )

        # ==================================================================
        # CONSULTA
        # ==================================================================

        elementos.append(
            Spacer(
                1,
                4 * mm
            )
        )

        consulta_box = Table(

            [
                [
                    [
                        Paragraph(
                            "CONSULTA",
                            estilo_label
                        ),

                        Spacer(
                            1,
                            1 * mm
                        ),

                        Paragraph(
                            _escape(consulta),
                            estilo_consulta
                        ),
                    ]
                ]
            ],

            colWidths=[
                ancho_util
            ],

            hAlign="LEFT",
        )

        consulta_box.setStyle(

            TableStyle(
                [

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        GRIS_50
                    ),

                    (
                        "LINEBEFORE",
                        (0, 0),
                        (0, -1),
                        4,
                        ROJO_NUCLEO
                    ),

                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        GRIS_200
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        14
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        14
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),
                ]
            )
        )

        elementos.append(
            consulta_box
        )

        # ==================================================================
        # RESUMEN
        # ==================================================================

        elementos.append(
            Spacer(
                1,
                3 * mm
            )
        )

        resumen = Table(

            [
                [

                    [
                        Paragraph(
                            str(
                                cantidad_productos
                            ),
                            estilo_resumen_numero
                        ),

                        Spacer(
                            1,
                            0.5 * mm
                        ),

                        Paragraph(
                            "PRODUCTOS",
                            estilo_resumen_label
                        ),
                    ],

                    [
                        Paragraph(
                            str(
                                stock_general
                            ),
                            estilo_resumen_numero
                        ),

                        Spacer(
                            1,
                            0.5 * mm
                        ),

                        Paragraph(
                            "STOCK TOTAL",
                            estilo_resumen_label
                        ),
                    ],

                    [
                        Paragraph(
                            _escape(
                                texto_dolar
                            ),
                            estilo_resumen_numero
                        ),

                        Spacer(
                            1,
                            0.5 * mm
                        ),

                        Paragraph(
                            "COTIZACIÓN",
                            estilo_resumen_label
                        ),
                    ],
                ]
            ],

            colWidths=[
                ancho_util / 3,
                ancho_util / 3,
                ancho_util / 3
            ],

            rowHeights=[
                15 * mm
            ],

            hAlign="LEFT",
        )

        resumen.setStyle(

            TableStyle(
                [

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        BLANCO
                    ),

                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        GRIS_200
                    ),

                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        GRIS_200
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),
                ]
            )
        )

        elementos.append(
            resumen
        )

        # ==================================================================
        # ESPACIO ANTES DE TABLA
        # ==================================================================

        elementos.append(
            Spacer(
                1,
                4 * mm
            )
        )

        # ==================================================================
        # TABLA DE PRODUCTOS
        # ==================================================================

        filas = [

            [

                Paragraph(
                    "CÓDIGO",
                    estilo_header
                ),

                Paragraph(
                    "DESCRIPCIÓN DEL PRODUCTO",
                    estilo_header
                ),

                Paragraph(
                    "PRECIO NETO",
                    estilo_header
                ),

                Paragraph(
                    "MDP",
                    estilo_header
                ),

                Paragraph(
                    "CABA",
                    estilo_header
                ),

                Paragraph(
                    "TOTAL",
                    estilo_header
                ),
            ]
        ]

        # ==================================================================
        # PRODUCTOS
        # ==================================================================

        for producto in productos:

            codigo = _escape(
                producto.get(
                    "sku",
                    ""
                )
            )

            descripcion = _escape(
                _obtener_descripcion(
                    producto
                )
            )

            precio = _precio(
                producto.get(
                    "precio_usd",
                    0
                )
            )

            stock_mdp = _stock_entero(
                producto.get(
                    "stock_mdp",
                    0
                )
            )

            stock_caba = _stock_entero(
                producto.get(
                    "stock_caba",
                    0
                )
            )

            stock_total = (
                stock_mdp
                + stock_caba
            )

            filas.append(

                [

                    Paragraph(
                        codigo,
                        estilo_codigo
                    ),

                    Paragraph(
                        descripcion,
                        estilo_descripcion
                    ),

                    Paragraph(
                        _escape(precio),
                        estilo_precio
                    ),

                    Paragraph(
                        str(stock_mdp),
                        estilo_stock
                    ),

                    Paragraph(
                        str(stock_caba),
                        estilo_stock
                    ),

                    Paragraph(
                        str(stock_total),
                        estilo_stock_total
                    ),
                ]
            )

        # ==================================================================
        # ANCHOS
        # ==================================================================

        anchos = [

            ancho_util * 0.085,

            ancho_util * 0.475,

            ancho_util * 0.145,

            ancho_util * 0.095,

            ancho_util * 0.095,

            ancho_util * 0.105,
        ]

        tabla = Table(

            filas,

            colWidths=anchos,

            repeatRows=1,

            hAlign="LEFT",

            splitByRow=True,
        )

        # ==================================================================
        # ESTILO TABLA
        # ==================================================================

        estilo_tabla = [

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                AZUL_NUCLEO
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                BLANCO
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "ALIGN",
                (0, 0),
                (0, -1),
                "LEFT"
            ),

            (
                "ALIGN",
                (1, 0),
                (1, -1),
                "LEFT"
            ),

            (
                "ALIGN",
                (2, 0),
                (2, -1),
                "RIGHT"
            ),

            (
                "ALIGN",
                (3, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, 0),
                7
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, 0),
                7
            ),

            (
                "TOPPADDING",
                (0, 1),
                (-1, -1),
                6
            ),

            (
                "BOTTOMPADDING",
                (0, 1),
                (-1, -1),
                6
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "LINEBELOW",
                (0, 1),
                (-1, -1),
                0.35,
                GRIS_200
            ),
        ]

        # ==================================================================
        # ZEBRA
        # ==================================================================

        for fila in range(
            1,
            len(filas)
        ):

            if fila % 2 == 0:

                estilo_tabla.append(

                    (
                        "BACKGROUND",
                        (0, fila),
                        (-1, fila),
                        GRIS_50
                    )
                )

            else:

                estilo_tabla.append(

                    (
                        "BACKGROUND",
                        (0, fila),
                        (-1, fila),
                        BLANCO
                    )
                )

        # ==================================================================
        # STOCK TOTAL
        # ==================================================================

        for fila in range(
            1,
            len(filas)
        ):

            producto = productos[
                fila - 1
            ]

            stock_mdp = _stock_entero(
                producto.get(
                    "stock_mdp",
                    0
                )
            )

            stock_caba = _stock_entero(
                producto.get(
                    "stock_caba",
                    0
                )
            )

            total = (
                stock_mdp
                + stock_caba
            )

            if total > 0:

                estilo_tabla.append(

                    (
                        "BACKGROUND",
                        (5, fila),
                        (5, fila),
                        VERDE_FONDO
                    )
                )

            else:

                estilo_tabla.append(

                    (
                        "BACKGROUND",
                        (5, fila),
                        (5, fila),
                        ROJO_FONDO
                    )
                )

                estilo_tabla.append(

                    (
                        "TEXTCOLOR",
                        (5, fila),
                        (5, fila),
                        ROJO_STOCK
                    )
                )

        tabla.setStyle(
            TableStyle(
                estilo_tabla
            )
        )

        elementos.append(
            tabla
        )

        # ==================================================================
        # AVISO FINAL
        # ==================================================================

        elementos.append(
            Spacer(
                1,
                3 * mm
            )
        )

        elementos.append(

            Paragraph(

                (
                    "Precios, impuestos y stocks validados "
                    "al momento de generar el documento. "
                    "La disponibilidad puede cambiar sin previo aviso."
                ),

                estilo_footer
            )
        )

        # ==================================================================
        # GENERAR PDF
        # ==================================================================

        doc.build(
            elementos
        )

        log.info(
            "PDF generado correctamente: %s",
            ruta
        )

        return ruta

    except Exception as e:

        log.exception(
            "Error generando PDF: %s",
            e
        )

        return None