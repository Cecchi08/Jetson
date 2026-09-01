"""
Asistente IA interno — Grupo Núcleo.

Combina:
- API de Grupo Núcleo (catálogo de productos).
- Modelo local Ollama.
- Búsqueda web (DuckDuckGo HTML).
- Generación de PDFs comparativos (estilo institucional Grupo Núcleo)
  cuando hay 3 o más productos.
- Servidor HTTP en puerto 9080 para descargar PDFs.
"""

import json
import logging
import re
import sys
import time
import os
import threading
from dataclasses import dataclass, field
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

import requests
import ollama
from bs4 import BeautifulSoup
import hashlib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException  
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# --- Parche para evitar el error de usedforsecurity en OpenSSL / ReportLab ---
_original_md5 = hashlib.md5
def _safe_md5(*args, **kwargs):
    kwargs.pop('usedforsecurity', None)
    return _original_md5(*args, **kwargs)
hashlib.md5 = _safe_md5
# --------------------------------------------------------------------------
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


# ============================================================
# CONFIGURACIÓN
# ============================================================

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-8k")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_CLIENT = ollama.Client(host=OLLAMA_HOST)

API_BASE = os.getenv("GN_API_BASE", "https://api.gruponucleosa.com")
GN_ID = int(os.getenv("GN_ID", "1163"))
USERNAME = os.getenv("GN_USERNAME", "pruebaapi")
PASSWORD = os.getenv("GN_PASSWORD", "123456789")

REQUEST_TIMEOUT = 20
OLLAMA_TIMEOUT_RETRIES = 2

HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
HTTP_PORT = int(os.getenv("HTTP_PORT", "9081"))

PDF_FOLDER = "pdf_generados"

# Logo institucional usado en el encabezado de los PDFs
LOGO_URL = "https://www.gruponucleo.com.ar/media/logo/stores/1/Logo_Nucleo_rojo-blanco.png"
LOGO_LOCAL_PATH = "logo_nucleo.png"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger("asistente")


# ============================================================
# SERVIDOR HTTP
# ============================================================

class PDFRequestHandler(SimpleHTTPRequestHandler):

    def _send_json(self, status_code, payload):
        contenido = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def do_GET(self):

        # ----------------------------------------------------
        # HEALTH CHECK
        # ----------------------------------------------------

        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "orchestrator"})
            return

        # ----------------------------------------------------
        # LISTADO DE PDFs
        # ----------------------------------------------------

        if self.path == "/pdfs" or self.path == "/pdfs/":

            try:

                archivos = []

                if os.path.exists(PDF_FOLDER):

                    for archivo in sorted(os.listdir(PDF_FOLDER), reverse=True):

                        if archivo.lower().endswith(".pdf"):

                            archivos.append(archivo)

                html = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>PDFs generados</title>
</head>
<body>
<h1>PDFs generados</h1>
<ul>
"""

                for archivo in archivos:

                    html += (
                        '<li>'
                        f'<a href="/pdfs/{archivo}" download>{archivo}</a>'
                        '</li>'
                    )

                if not archivos:
                    html += "<li>No hay PDFs generados.</li>"

                html += """
</ul>
</body>
</html>
"""

                contenido = html.encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(contenido)))
                self.end_headers()
                self.wfile.write(contenido)

                return

            except Exception as e:

                log.error("Error listando PDFs: %s", e)
                self.send_error(500, str(e))

                return

        # ----------------------------------------------------
        # ARCHIVOS PDF
        # ----------------------------------------------------

        if self.path.startswith("/pdfs/"):

            nombre = self.path[len("/pdfs/"):]
            nombre = os.path.basename(nombre)

            ruta = os.path.abspath(os.path.join(PDF_FOLDER, nombre))
            carpeta = os.path.abspath(PDF_FOLDER)

            if not ruta.startswith(carpeta + os.sep):
                self.send_error(403)
                return

            if not os.path.isfile(ruta):
                self.send_error(404, "PDF no encontrado")
                return

            try:
                with open(ruta, "rb") as archivo:
                    contenido = archivo.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{nombre}"'
                )
                self.send_header("Content-Length", str(len(contenido)))
                self.end_headers()
                self.wfile.write(contenido)

                return

            except Exception as e:
                log.error("Error enviando PDF: %s", e)
                self.send_error(500, str(e))
                return

        self.send_error(404, "Recurso no encontrado")

    def do_POST(self):
        if self.path != "/chat":
            self.send_error(404, "Recurso no encontrado")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            log.error("JSON inválido en /chat: %s", exc)
            self._send_json(400, {"success": False, "error": "JSON inválido"})
            return

        mensaje = payload.get("message")
        if not isinstance(mensaje, str) or not mensaje.strip():
            self._send_json(400, {"success": False, "error": "El campo message es obligatorio"})
            return

        history = payload.get("history", [])
        sesion = SesionChat(historial=normalizar_historial(history))

        try:
            respuesta = procesar_mensaje(mensaje.strip(), api_global, sesion)
            self._send_json(200, {"success": True, "response": respuesta})
        except Exception as exc:
            log.error("Error interno en /chat: %s", exc)
            self._send_json(500, {"success": False, "error": "Error interno del orquestador"})

    def log_message(self, format, *args):
        log.info("HTTP: " + format, *args)


def iniciar_servidor_http():

    os.makedirs(PDF_FOLDER, exist_ok=True)

    servidor = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), PDFRequestHandler)

    log.info("Servidor HTTP iniciado en 0.0.0.0:%s", HTTP_PORT)

    try:

        servidor.serve_forever()

    except Exception as e:

        log.error("Servidor HTTP detenido: %s", e)

    finally:

        servidor.server_close()


# ============================================================
# API GRUPO NÚCLEO
# ============================================================

class GrupoNucleoAPI:

    def __init__(self):

        self.token = None
        self.catalogo = []
        self.cotizacion = None  # se completa en main() tras consultar la API

    def login(self):

        url = f"{API_BASE}/Authentication/Login"

        payload = {
            "loginModel": {
                "id": GN_ID,
                "username": USERNAME,
                "password": PASSWORD
            }
        }

        response = requests.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        log.info("LOGIN STATUS: %s", response.status_code)

        response.raise_for_status()

        self.token = response.text.strip().strip('"')

        log.info("Token obtenido correctamente.")

    def _get_con_reintento(self, url):

        if not self.token:

            self.login()

        headers = {
            "accept": "*/*",
            "Authorization": f"Bearer {self.token}"
        }

        response = requests.get(url, headers=headers, timeout=60)

        if response.status_code == 401:

            log.warning("Token vencido, renovando...")

            self.login()

            headers["Authorization"] = f"Bearer {self.token}"

            response = requests.get(url, headers=headers, timeout=60)

        return response

    def obtener_catalogo(self):

        url = f"{API_BASE}/API_V1/GetCatalog"

        response = self._get_con_reintento(url)

        log.info("CATALOG STATUS: %s", response.status_code)

        response.raise_for_status()

        data = response.json()

        if isinstance(data, list):

            self.catalogo = data

        elif isinstance(data, dict):

            self.catalogo = (
                data.get("items")
                or data.get("data")
                or data.get("productos")
                or []
            )

        else:

            self.catalogo = []

        log.info("Catálogo obtenido: %s productos", len(self.catalogo))

        if not self.catalogo:

            log.warning("El catálogo llegó vacío.")

        return self.catalogo


# ============================================================
# COTIZACIÓN USD
# ============================================================

def obtener_cotizacion_usd(api):

    try:

        url = f"{API_BASE}/API_V1/GetUSDExchange"

        response = api._get_con_reintento(url)

        log.info("USD EXCHANGE STATUS: %s", response.status_code)

        response.raise_for_status()

        data = response.json()

        log.info("Cotización USD obtenida: %s", data)

        if isinstance(data, (int, float)):

            return float(data)

        if isinstance(data, str):

            try:

                return float(data.replace(",", "."))

            except Exception:

                pass

        if isinstance(data, dict):

            posibles = [
                "valor", "value", "cotizacion", "exchange",
                "usd", "precio", "venta", "rate"
            ]

            for campo in posibles:

                if campo in data:

                    try:

                        return float(str(data[campo]).replace(",", "."))

                    except Exception:

                        pass

            for valor in data.values():

                try:

                    numero = float(str(valor).replace(",", "."))

                    if numero > 100:

                        return numero

                except Exception:

                    pass

        log.warning("No se pudo determinar la cotización USD.")

        return None

    except Exception as e:

        log.error("Error obteniendo cotización USD: %s", e)

        return None


# ============================================================
# BÚSQUEDA WEB
# ============================================================

def buscar_web(consulta, limite=10):

    log.info("TOOL buscar_web: %s", consulta)

    try:

        url = "https://html.duckduckgo.com/html/"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            )
        }

        response = requests.get(
            url, params={"q": consulta}, headers=headers, timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        resultados = []

        for resultado in soup.select(".result")[:limite]:

            titulo = resultado.select_one(".result__title")
            enlace = resultado.select_one(".result__a")
            snippet = resultado.select_one(".result__snippet")

            if not titulo or not enlace:

                continue

            resultados.append({
                "titulo": titulo.get_text(" ", strip=True),
                "url": enlace.get("href", ""),
                "descripcion": (
                    snippet.get_text(" ", strip=True) if snippet else ""
                )
            })

        log.info("Resultados web encontrados: %s", len(resultados))

        return resultados

    except Exception as e:

        log.error("Error en buscar_web: %s", e)

        return {"error": True, "mensaje": str(e)}


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar(texto):

    if texto is None:

        return ""

    texto = str(texto).lower()

    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o",
        "ú": "u", "ü": "u", "ñ": "n"
    }

    for viejo, nuevo in reemplazos.items():

        texto = texto.replace(viejo, nuevo)

    texto = re.sub(r"[^a-z0-9]+", " ", texto)

    return " ".join(texto.split())


def tokens(texto):

    return [p for p in normalizar(texto).split() if len(p) >= 2]


# ============================================================
# DETECCIÓN DE CATEGORÍA
# ============================================================

def detectar_categoria_consulta(consulta):

    q = normalizar(consulta)

    motherboard_palabras = [
        "motherboard", "motherboards", "mother",
        "placa madre", "placas madre", "placa base", "placas base"
    ]

    if any(palabra in q for palabra in motherboard_palabras):

        return "motherboard"

    cpu_palabras = [
        "micro", "micros", "microprocesador", "microprocesadores",
        "procesador", "procesadores", "cpu", "ryzen",
        "core i3", "core i5", "core i7", "core i9"
    ]

    if any(palabra in q for palabra in cpu_palabras):

        return "cpu"

    gpu_palabras = [
        "placa de video", "placas de video", "gpu",
        "rtx", "gtx", "radeon", "rx "
    ]

    if any(palabra in q for palabra in gpu_palabras):

        return "gpu"

    ram_palabras = [
        "ram", "memoria ram", "memorias ram",
        "ddr3", "ddr4", "ddr5", "udimm", "sodimm"
    ]

    if any(palabra in q for palabra in ram_palabras):

        return "ram"

    almacenamiento_palabras = [
        "ssd", "nvme", "disco", "discos", "hdd", "m2", "m.2", "almacenamiento"
    ]

    if any(palabra in q for palabra in almacenamiento_palabras):

        return "almacenamiento"

    fuente_palabras = ["fuente", "fuentes", "psu", "power supply"]

    if any(palabra in q for palabra in fuente_palabras):

        return "fuente"

    return None


# ============================================================
# DETECCIÓN DE CONSULTAS ESPECIALES
# ============================================================

def es_consulta_deportiva(consulta):

    q = normalizar(consulta)

    palabras = [
        "juega", "partido", "vs", "versus", "fixture", "resultado",
        "torneo", "liga", "campeonato", "final", "semifinal",
        "proximo", "hoy"
    ]

    return any(palabra in q for palabra in palabras)


def es_consulta_ram(consulta):

    return detectar_categoria_consulta(consulta) == "ram"


# ============================================================
# IDENTIFICACIÓN DE PRODUCTOS
# ============================================================

def texto_producto(producto):

    campos = [
        producto.get("categoria", ""),
        producto.get("subcategoria", ""),
        producto.get("item_desc_0", ""),
        producto.get("item_desc_1", ""),
        producto.get("marca", ""),
        producto.get("codigo", ""),
        producto.get("ean", ""),
        producto.get("partNumber", "")
    ]

    return normalizar(" ".join(str(x) for x in campos if x is not None))


# ============================================================
# FILTROS DE CATEGORÍA
# ============================================================

def es_memoria_ram(producto):

    texto = texto_producto(producto)

    subcategoria = normalizar(producto.get("subcategoria", ""))

    if subcategoria == "memorias":

        return True

    patrones = ["udimm", "sodimm", "ddr3", "ddr4", "ddr5", "memoria ram"]

    return any(p in texto for p in patrones)


def es_memoria_sd(producto):

    texto = texto_producto(producto)

    patrones = [
        "memorias sd", "memoria sd", "memoria micro sd",
        "micro sd", "microsd", "sdxc", "sdhc", "tarjeta sd"
    ]

    return any(p in texto for p in patrones)


def es_motherboard(producto):

    texto = texto_producto(producto)
    categoria = normalizar(producto.get("categoria", ""))
    subcategoria = normalizar(producto.get("subcategoria", ""))

    patrones = [
        "motherboard", "mother board", "placa madre",
        "placa base", "mainboard", "mother "
    ]

    if any(p in texto for p in patrones):

        return True

    if "mother" in categoria:

        return True

    if "mother" in subcategoria:

        return True

    return False


def es_cpu(producto):

    texto = texto_producto(producto)
    categoria = normalizar(producto.get("categoria", ""))
    subcategoria = normalizar(producto.get("subcategoria", ""))

    patrones = [
        "procesador", "microprocesador", "micro amd", "micro intel",
        "ryzen", "core i3", "core i5", "core i7", "core i9"
    ]

    if any(p in texto for p in patrones):

        return True

    if "micro" in categoria:

        return True

    if "procesador" in categoria:

        return True

    if "micro" in subcategoria:

        return True

    return False


def es_gpu(producto):

    texto = texto_producto(producto)

    patrones = [
        "placa de video", "placa video", "geforce",
        "rtx ", "gtx ", "radeon", "rx "
    ]

    return any(p in texto for p in patrones)


def es_almacenamiento(producto):

    texto = texto_producto(producto)

    patrones = ["ssd", "nvme", "disco rigido", "disco duro", "hdd", "m.2", "m2"]

    return any(p in texto for p in patrones)


def es_fuente(producto):

    texto = texto_producto(producto)

    patrones = ["fuente", "power supply", "psu"]

    return any(p in texto for p in patrones)


def producto_pertenece_categoria(producto, categoria):

    if categoria is None:

        return True

    if categoria == "ram":

        return es_memoria_ram(producto) and not es_memoria_sd(producto)

    if categoria == "motherboard":

        return es_motherboard(producto)

    if categoria == "cpu":

        return es_cpu(producto)

    if categoria == "gpu":

        return es_gpu(producto)

    if categoria == "almacenamiento":

        return es_almacenamiento(producto)

    if categoria == "fuente":

        return es_fuente(producto)

    return True


# ============================================================
# PRODUCTO RESUMIDO
# ============================================================

def resumir_producto(producto):

    return {
        "item_id": producto.get("item_id"),
        "sku": str(producto.get("codigo", "")),
        "codigo": str(producto.get("codigo", "")),
        "ean": str(producto.get("ean", "")),
        "partNumber": str(producto.get("partNumber", "")),
        "nombre": producto.get("item_desc_0", ""),
        "descripcion": producto.get("item_desc_1", ""),
        "marca": producto.get("marca", ""),
        "categoria": producto.get("categoria", ""),
        "subcategoria": producto.get("subcategoria", ""),
        "precio_usd": producto.get("precioNeto_USD", 0),
        "stock_mdp": producto.get("stock_mdp", 0),
        "stock_caba": producto.get("stock_caba", 0)
    }


# ============================================================
# BUSCADOR INTELIGENTE
# ============================================================

def buscar_productos(consulta, catalogo):

    q = normalizar(consulta)
    q_tokens = tokens(consulta)

    categoria_consulta = detectar_categoria_consulta(consulta)

    log.info("Categoría detectada: %s", categoria_consulta)

    ddr_filtro = None

    if "ddr5" in q:

        ddr_filtro = "ddr5"

    elif "ddr4" in q:

        ddr_filtro = "ddr4"

    elif "ddr3" in q:

        ddr_filtro = "ddr3"

    resultados = []

    for producto in catalogo:

        texto = texto_producto(producto)
        nombre = normalizar(producto.get("item_desc_0", ""))
        descripcion = normalizar(producto.get("item_desc_1", ""))
        marca = normalizar(producto.get("marca", ""))
        categoria = normalizar(producto.get("categoria", ""))
        subcategoria = normalizar(producto.get("subcategoria", ""))
        codigo = normalizar(producto.get("codigo", ""))
        ean = normalizar(producto.get("ean", ""))
        part_number = normalizar(producto.get("partNumber", ""))

        if not producto_pertenece_categoria(producto, categoria_consulta):

            continue

        if ddr_filtro:

            if ddr_filtro not in texto:

                continue

        score = 0

        if q and q in nombre:
            score += 150
        if q and q in descripcion:
            score += 80
        if q and q in marca:
            score += 60
        if q and q in subcategoria:
            score += 40
        if q and q in categoria:
            score += 40
        if q and q in part_number:
            score += 100
        if q and q in codigo:
            score += 130
        if q and q in ean:
            score += 130

        tokens_encontrados = 0

        for token in q_tokens:

            encontrado = False

            if token in nombre:
                score += 20
                encontrado = True
            if token in descripcion:
                score += 8
                encontrado = True
            if token in marca:
                score += 10
                encontrado = True
            if token in categoria:
                score += 6
                encontrado = True
            if token in subcategoria:
                score += 6
                encontrado = True
            if token in part_number:
                score += 12
                encontrado = True
            if token in codigo:
                score += 15
                encontrado = True

            if encontrado:

                tokens_encontrados += 1

        if categoria_consulta == "motherboard":
            score += 100
        elif categoria_consulta == "cpu":
            score += 100
        elif categoria_consulta == "gpu":
            score += 100
        elif categoria_consulta == "ram":
            score += 100
            if ddr_filtro:
                score += 50
        elif categoria_consulta == "almacenamiento":
            score += 100
        elif categoria_consulta == "fuente":
            score += 100

        if q_tokens:

            porcentaje = tokens_encontrados / len(q_tokens)

            if len(q_tokens) >= 2 and porcentaje < 0.5:

                continue

        if score <= 0:

            continue

        resultados.append((score, producto))

    resultados.sort(key=lambda x: x[0], reverse=True)

    productos_finales = []
    vistos = set()

    for score, producto in resultados:

        identificador = (
            producto.get("item_id")
            or producto.get("codigo")
            or producto.get("partNumber")
        )

        if identificador in vistos:

            continue

        vistos.add(identificador)

        productos_finales.append(resumir_producto(producto))

    log.info("Productos finales encontrados: %s", len(productos_finales))

    return productos_finales


# ============================================================
# GENERACIÓN DE PDF (estilo institucional Grupo Núcleo)
# ============================================================

def _obtener_logo():
    """
    Descarga y cachea en disco el logo de Grupo Núcleo.
    Si no hay conexión o la URL falla, devuelve None
    y el PDF se genera sin logo (no rompe la generación).
    """
    if os.path.exists(LOGO_LOCAL_PATH):

        return LOGO_LOCAL_PATH

    try:

        respuesta = requests.get(LOGO_URL, timeout=10)
        respuesta.raise_for_status()

        with open(LOGO_LOCAL_PATH, "wb") as archivo:

            archivo.write(respuesta.content)

        return LOGO_LOCAL_PATH

    except Exception as e:

        log.warning("No se pudo descargar el logo: %s", e)
        return None


def generar_pdf_productos(productos, consulta, cotizacion=None):
    """
    Genera el PDF comparativo con estilo institucional Grupo Núcleo:
    logo, título, fecha de emisión, cotización del dólar GN,
    consulta realizada y tabla de productos con filas alternadas.

    Parámetros:
        productos (list[dict]): productos ya resumidos (resumir_producto).
        consulta (str): texto de búsqueda, se muestra como referencia.
        cotizacion (float | None): dólar GN a mostrar en el encabezado.

    Retorna:
        str | None: ruta absoluta al PDF generado, o None si falló.
    """
    try:

        os.makedirs(PDF_FOLDER, exist_ok=True)

        nombre_archivo = normalizar(consulta)
        nombre_archivo = re.sub(r"[^a-z0-9]+", "_", nombre_archivo).strip("_")

        if not nombre_archivo:

            nombre_archivo = "productos"

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        ruta = os.path.abspath(
            os.path.join(PDF_FOLDER, f"{nombre_archivo}_{timestamp}.pdf")
        )

        COLOR_GRIS_CLARO = colors.HexColor("#F5F5F5")
        COLOR_GRIS_TEXTO = colors.HexColor("#555555")
        COLOR_NEGRO = colors.HexColor("#1A1A1A")
        COLOR_AZUL = colors.HexColor("#111826")
        COLOR_AZUL_OSCURO = colors.HexColor("#0B1220")

        doc = SimpleDocTemplate(
            ruta, pagesize=landscape(A4),
            leftMargin=15 * mm, rightMargin=15 * mm,
            topMargin=12 * mm, bottomMargin=15 * mm,
        )

        elementos = []
        estilos = getSampleStyleSheet()

        estilo_titulo = ParagraphStyle(
            "TituloNucleo", parent=estilos["Heading1"],
            fontSize=18, textColor=colors.white, spaceAfter=2,
            leading=20, fontName="Helvetica-Bold",
        )
        estilo_subtitulo = ParagraphStyle(
            "SubtituloNucleo", parent=estilos["Normal"],
            fontSize=9, textColor=colors.white, spaceAfter=10,
            leading=12,
        )
        estilo_consulta = ParagraphStyle(
            "ConsultaNucleo", parent=estilos["Normal"], fontSize=10, spaceAfter=2,
        )
        estilo_dolar = ParagraphStyle(
            "DolarNucleo", parent=estilos["Normal"],
            fontSize=10, spaceAfter=10, fontName="Helvetica-Bold",
        )
        estilo_celda = ParagraphStyle(
            "CeldaNucleo", parent=estilos["Normal"], fontSize=8.5, leading=11,
        )
        estilo_footer = ParagraphStyle(
            "FooterNucleo", parent=estilos["Normal"],
            fontSize=7.5, textColor=COLOR_GRIS_TEXTO,
        )

        # ---------------- Encabezado superior azul ----------------
        logo_path = _obtener_logo()
        fecha_emision = time.strftime("%d/%m/%Y, %H:%M:%S")
        texto_dolar = (
            f"Dólar GN: {cotizacion:.0f}" if cotizacion else "Dólar GN: no disponible"
        )

        encabezado_celdas = []

        if logo_path:

            logo = Image(logo_path, width=28 * mm, height=10 * mm)
            encabezado_celdas = [
                logo,
                Paragraph("Lista de productos Grupo Núcleo", estilo_titulo),
                Paragraph(f"Emitido: {fecha_emision}", estilo_subtitulo),
                Paragraph(texto_dolar, estilo_subtitulo),
            ]

            encabezado = Table(
                [encabezado_celdas],
                colWidths=[30 * mm, 80 * mm, 36 * mm, 30 * mm],
            )

        else:

            encabezado = Table(
                [[
                    Paragraph("Lista de productos Grupo Núcleo", estilo_titulo),
                    Paragraph(f"Emitido: {fecha_emision}", estilo_subtitulo),
                    Paragraph(texto_dolar, estilo_subtitulo),
                ]],
                colWidths=[90 * mm, 42 * mm, 38 * mm],
            )

        encabezado.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_AZUL),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("ALIGN", (1, 0), (1, 0), "LEFT"),
            ("LEFTPADDING", (0, 0), (-1, 0), 6),
            ("RIGHTPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, 0), 0.5, COLOR_AZUL_OSCURO),
        ]))

        elementos.append(encabezado)
        elementos.append(Spacer(1, 4 * mm))
        elementos.append(Paragraph(f"Consulta: {consulta}", estilo_consulta))
        elementos.append(Paragraph(texto_dolar, estilo_dolar))
        elementos.append(Spacer(1, 2 * mm))

        # ---------------- Tabla de productos ----------------
        encabezados = [
            "Código", "Descripción completa", "Precio neto USD",
            "Stock MDP", "Stock CABA", "Stock total",
        ]

        filas = [encabezados]

        for producto in productos:

            codigo = str(producto.get("sku", ""))
            descripcion = str(
                producto.get("nombre", "") or producto.get("descripcion", "")
            )

            try:

                precio = float(producto.get("precio_usd", 0))

            except Exception:

                precio = 0

            stock_mdp = producto.get("stock_mdp", 0) or 0
            stock_caba = producto.get("stock_caba", 0) or 0

            try:

                stock_total = int(stock_mdp) + int(stock_caba)

            except Exception:

                stock_total = ""

            filas.append([
                codigo,
                Paragraph(descripcion, estilo_celda),
                f"USD {precio:,.2f}",
                str(stock_mdp),
                str(stock_caba),
                str(stock_total),
            ])

        ancho = doc.width

        anchos_columnas = [
            ancho * 0.10, ancho * 0.42, ancho * 0.18,
            ancho * 0.10, ancho * 0.10, ancho * 0.10,
        ]

        tabla = Table(filas, colWidths=anchos_columnas, repeatRows=1)

        estilo_tabla = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_AZUL_OSCURO),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, 0), 0.75, COLOR_AZUL_OSCURO),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ]

        # Filas alternadas (zebra) para facilitar la lectura
        for i in range(1, len(filas)):

            if i % 2 == 0:

                estilo_tabla.append(
                    ("BACKGROUND", (0, i), (-1, i), COLOR_GRIS_CLARO)
                )

        tabla.setStyle(TableStyle(estilo_tabla))
        elementos.append(tabla)

        elementos.append(Spacer(1, 6 * mm))
        elementos.append(Paragraph(
            "Precios, stocks e IVA validados al momento de generar el PDF. "
            "La disponibilidad puede cambiar sin previo aviso.",
            estilo_footer,
        ))

        def _numero_pagina(canvas, documento):
            """Dibuja el número de página en el pie de cada hoja."""
            canvas.saveState()
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(COLOR_GRIS_TEXTO)
            canvas.drawRightString(
                A4[0] - 15 * mm, 10 * mm, f"Página {documento.page}"
            )
            canvas.restoreState()

        doc.build(elementos, onFirstPage=_numero_pagina, onLaterPages=_numero_pagina)

        log.info("PDF generado correctamente: %s", ruta)

        return ruta

    except Exception as e:

        log.error("Error generando PDF: %s", e)

        return None


# ============================================================
# OLLAMA
# ============================================================

def _chat_ollama(prompt, num_ctx):

    ultimo_error = None

    for intento in range(1 + OLLAMA_TIMEOUT_RETRIES):

        try:

            respuesta = OLLAMA_CLIENT.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"num_ctx": num_ctx}
            )

            contenido = respuesta["message"].get("content", "").strip()

            if contenido:
                return contenido

            ultimo_error = "Respuesta vacía de Ollama"

        except Exception as e:
            ultimo_error = str(e)

        log.warning(
            "Ollama falló (intento %s/%s): %s",
            intento + 1, OLLAMA_TIMEOUT_RETRIES + 1, ultimo_error
        )

        time.sleep(1)

    raise RuntimeError("Ollama no respondió: " + str(ultimo_error))


# ============================================================
# INTENCIÓN
# ============================================================

def detectar_intencion(mensaje):

    prompt = """

Analizá el mensaje del usuario y devolvé
ÚNICAMENTE JSON válido.

NO uses markdown.
NO expliques nada.

Formato:

{
  "accion": "buscar" | "precio" | "stock" | "web" | "conversacion",
  "consulta": "texto de búsqueda"
}

REGLAS IMPORTANTES:

buscar:
El usuario quiere saber qué productos tenemos.

precio:
El usuario quiere saber cuánto cuesta uno
o varios productos.

stock:
El usuario pregunta cuántas unidades hay.

web:
SOLO usar para información que NO provenga
del catálogo de la empresa y que requiera Internet,
actualidad o información cambiante.

Ejemplos de web:
- partidos de fútbol
- resultados deportivos
- noticias
- clima
- presidente actual
- eventos actuales
- información de personas
- horarios actuales

MUY IMPORTANTE:

Si el usuario pregunta por PRODUCTOS de la empresa,
SIEMPRE usá "buscar", "precio" o "stock".

NO uses "web" para buscar productos.

Por ejemplo:

"lista de motherboards AM5"
=> buscar

"que mothers AM5 tenemos"
=> buscar

"mostrame micros Ryzen 5"
=> buscar

"que placas de video RTX tenemos"
=> buscar

"cuanto sale una motherboard AM5"
=> precio

"cuantas motherboards AM5 tenemos"
=> stock

"contra quien juega Boca hoy"
=> web

"cuando juega River"
=> web

"quien es el presidente actual"
=> web

IMPORTANTE:

Palabras como "hoy", "ahora" o "actualmente"
NO convierten automáticamente una consulta de
producto en web.

Si se habla de un producto del catálogo,
seguí usando catálogo.

Ejemplo:

"que mothers AM5 tenemos hoy"
=> buscar

"que micros Ryzen tenemos actualmente"
=> buscar

EJEMPLOS:

Usuario:
que memorias ram ddr5 tenemos

Respuesta:
{"accion":"buscar","consulta":"memorias ram ddr5"}

Usuario:
cuantos ryzen 7 7700x tenemos

Respuesta:
{"accion":"stock","consulta":"ryzen 7 7700x"}

Usuario:
cuanto sale el ryzen 7 7700x

Respuesta:
{"accion":"precio","consulta":"ryzen 7 7700x"}

Usuario:
lista de motherboards am5

Respuesta:
{"accion":"buscar","consulta":"motherboards am5"}

Usuario:
que mothers am5 tenemos

Respuesta:
{"accion":"buscar","consulta":"motherboards am5"}

Usuario:
contra quien juega boca hoy

Respuesta:
{"accion":"web","consulta":"Boca Juniors partido hoy"}

Usuario:
cuando juega river

Respuesta:
{"accion":"web","consulta":"River Plate próximo partido"}

Usuario:
quien es el presidente de argentina

Respuesta:
{"accion":"web","consulta":"presidente de Argentina actual"}

Usuario:
hola

Respuesta:
{"accion":"conversacion","consulta":""}

MENSAJE DEL USUARIO:

""" + mensaje

    try:

        contenido = _chat_ollama(prompt, num_ctx=4096)

    except RuntimeError as e:

        log.error("detectar_intencion: %s", e)

        return {"accion": "buscar", "consulta": mensaje}

    try:

        return json.loads(contenido)

    except json.JSONDecodeError:

        inicio = contenido.find("{")
        fin = contenido.rfind("}")

        if inicio != -1 and fin != -1:

            try:

                return json.loads(contenido[inicio:fin + 1])

            except Exception:

                pass

    return {"accion": "buscar", "consulta": mensaje}


# ============================================================
# RESPUESTA FINAL
# ============================================================

def generar_respuesta(mensaje, resultado, historial):

    contexto = ""

    if historial:

        contexto = "Conversación anterior:\n" + "\n".join(historial[-8:])

    prompt = f"""

Sos un asistente interno de una empresa.

Respondé al usuario en español argentino.

Usá SOLAMENTE la información proporcionada.

No inventes datos.

No muestres JSON.

No menciones tools, funciones,
Python, Ollama ni procesos internos.

============================================================
PRODUCTOS
============================================================

Cuando respondas sobre productos,
usá exactamente este formato:

SKU: XXXXX
Descripción: descripción completa
Valor: USD $XXX.XX
Stock MDP: X unidades
Stock CABA: X unidades

Separá cada producto con una línea en blanco.

NO agregues equivalentes en pesos.

NO agregues explicaciones innecesarias.

============================================================
BÚSQUEDA WEB
============================================================

Si los datos provienen de una búsqueda web:

Usá la información encontrada.

Está PROHIBIDO decir:

"buscalo en Google"

"fijate en Sofascore"

"consultá la página"

"te recomiendo visitar..."

El usuario espera que VOS respondas
usando los resultados obtenidos.

REGLA ANTI-INVENCIÓN:

Un dato concreto como fecha, hora, rival,
resultado, marcador o lugar solamente puede
aparecer si está escrito en los resultados
proporcionados.

Si no aparece, decilo claramente.

============================================================
RAM
============================================================

Si el usuario preguntó por RAM:

Solamente considerá:

UDIMM
SODIMM
DDR3
DDR4
DDR5

No consideres memorias SD como RAM.

============================================================

{contexto}

MENSAJE ACTUAL:

{mensaje}

DATOS OBTENIDOS:

{json.dumps(resultado, ensure_ascii=False)}

Generá únicamente la respuesta final.

"""

    try:

        return _chat_ollama(prompt, num_ctx=8192)

    except RuntimeError as e:

        log.error("generar_respuesta: %s", e)

        return "Perdón, tuve un problema para generar la respuesta."


# ============================================================
# SESIÓN
# ============================================================

def normalizar_historial(history):
    if not history:
        return []

    historial = []

    for item in history:
        if isinstance(item, dict):
            role = str(item.get("role", "user")).lower()
            content = item.get("content", "")
            if isinstance(content, str) and content.strip():
                etiqueta = "Usuario" if role == "user" else "Asistente"
                historial.append(f"{etiqueta}: {content.strip()}")
        elif isinstance(item, str) and item.strip():
            historial.append(item.strip())

    return historial


@dataclass
class SesionChat:

    historial: list = field(default_factory=list)
    ultimos_productos: list = field(default_factory=list)

    def registrar_turno(self, mensaje, respuesta):

        self.historial.append(f"Usuario: {mensaje}")
        self.historial.append(f"Asistente: {respuesta}")

        if len(self.historial) > 16:

            self.historial = self.historial[-16:]


PALABRAS_CONTEXTO = [
    "este", "esta", "ese", "esa", "el anterior", "la anterior",
    "cada uno", "cuanto sale", "cuanto cuesta", "precio"
]


def resolver_consulta_con_contexto(consulta, sesion):

    consulta_normalizada = normalizar(consulta)

    necesita_contexto = any(
        p in consulta_normalizada for p in PALABRAS_CONTEXTO
    )

    if necesita_contexto and sesion.ultimos_productos:

        if len(sesion.ultimos_productos) == 1:

            return sesion.ultimos_productos[0]["nombre"]

    return consulta


# ============================================================
# PROCESAR MENSAJE
# ============================================================

def procesar_mensaje(mensaje, api, sesion):

    intencion = detectar_intencion(mensaje)

    accion = intencion.get("accion", "buscar")
    consulta = intencion.get("consulta", mensaje)

    log.info("Acción: %s | Consulta: %s", accion, consulta)

    # ========================================================
    # CONVERSACIÓN
    # ========================================================

    if accion == "conversacion":

        respuesta = generar_respuesta(mensaje, {}, sesion.historial)

    # ========================================================
    # WEB
    # ========================================================

    elif accion == "web":

        limite_web = 10 if es_consulta_deportiva(consulta) else 6

        resultados_web = buscar_web(consulta, limite=limite_web)

        datos = {
            "tipo": "busqueda_web",
            "consulta": consulta,
            "resultados": resultados_web
        }

        respuesta = generar_respuesta(mensaje, datos, sesion.historial)

    # ========================================================
    # CATÁLOGO
    # ========================================================

    else:

        consulta = resolver_consulta_con_contexto(consulta, sesion)

        resultados = buscar_productos(consulta, api.catalogo)

        sesion.ultimos_productos = resultados

        log.info("Buscador: %s resultados", len(resultados))

        # ====================================================
        # PDF
        # ====================================================

        pdf_generado = None

        if len(resultados) >= 3:

            log.info(
                "Hay %s productos. Generando comparativa PDF...",
                len(resultados)
            )

            pdf_generado = generar_pdf_productos(
                resultados,
                consulta,
                api.cotizacion,
            )

        # ====================================================
        # RESPUESTA CON ENLACE AL PDF
        # ====================================================

        if pdf_generado:

            nombre_pdf = os.path.basename(pdf_generado)

            enlace_pdf = (
                f"http://172.15.0.202:{HTTP_PORT}/pdfs/{nombre_pdf}"
            )

            respuesta = (
                "Preparé una comparativa "
                f"con {len(resultados)} productos.\n\n"
                "Podés descargarla acá:\n"
                f"{enlace_pdf}"
            )

        else:

            datos = {
                "accion": accion,
                "consulta": consulta,
                "cantidad_resultados": len(resultados),
                "productos": resultados
            }

            respuesta = generar_respuesta(mensaje, datos, sesion.historial)

    # ========================================================
    # MEMORIA
    # ========================================================

    sesion.registrar_turno(mensaje, respuesta)

    return respuesta


# ============================================================
# MAIN
# ============================================================

api_global = None


def initialize_runtime():
    global api_global

    if api_global is not None:
        return api_global

    api = GrupoNucleoAPI()

    try:
        api.obtener_catalogo()
        api.cotizacion = obtener_cotizacion_usd(api)
    except Exception as e:
        log.error("ERROR AL OBTENER EL CATÁLOGO: %s", e)
        raise

    os.makedirs(PDF_FOLDER, exist_ok=True)
    api_global = api
    return api


def main():
    global api_global

    print("=" * 60)
    print("ASISTENTE IA - EMPRESA")
    print("=" * 60)
    print()
    print(f"Modelo: {OLLAMA_MODEL}")
    print(f"API: {API_BASE}")
    print()

    try:
        api = initialize_runtime()
    except Exception:
        return

    if "--console" in sys.argv:
        print()
        print("=" * 60)
        print("ASISTENTE LISTO")
        print("Escribí 'salir' para terminar.")
        print()
        print(f"Servidor HTTP: puerto {HTTP_PORT}")
        print(f"Health: http://127.0.0.1:{HTTP_PORT}/health")
        print(f"PDFs:   http://127.0.0.1:{HTTP_PORT}/pdfs/")
        print("=" * 60)
        print()

        sesion = SesionChat()

        while True:
            try:
                mensaje = input("Vos: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nSaliendo...")
                break

            if not mensaje:
                continue

            if normalizar(mensaje) in ["salir", "exit", "quit"]:
                print("Hasta luego.")
                break

            try:
                inicio = time.time()
                respuesta = procesar_mensaje(mensaje, api, sesion)
                tiempo = time.time() - inicio

                print()
                print(f"Qwen: {respuesta}")
                print()
                log.info("Tiempo total: %.2f segundos", tiempo)

            except Exception as e:
                log.error("ERROR procesando mensaje: %s", e)
        return

    print()
    print("=" * 60)
    print("ASISTENTE LISTO")
    print("Servicio HTTP activo.")
    print(f"Servidor HTTP: puerto {HTTP_PORT}")
    print(f"Health: http://127.0.0.1:{HTTP_PORT}/health")
    print(f"PDFs:   http://127.0.0.1:{HTTP_PORT}/pdfs/")
    print("=" * 60)
    print()

    iniciar_servidor_http()


# ============================================================
# FASTAPI HTTP
# ============================================================

app = FastAPI(title="Orquestador IA", version="1.0.0")


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = Field(default_factory=list)


@app.on_event("startup")
async def startup_event():
    initialize_runtime()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/pdfs")
def list_pdfs_route():
    archivos = []
    if os.path.exists(PDF_FOLDER):
        for archivo in sorted(os.listdir(PDF_FOLDER), reverse=True):
            if archivo.lower().endswith(".pdf"):
                archivos.append({"name": archivo, "url": f"/pdfs/{archivo}"})
    return {"files": archivos}


@app.get("/pdfs/{filename}")
def get_pdf_route(filename: str):
    safe_name = os.path.basename(filename)
    target = os.path.abspath(os.path.join(PDF_FOLDER, safe_name))
    base = os.path.abspath(PDF_FOLDER)
    if not target.startswith(base + os.sep):
        raise HTTPException(status_code=403, detail="Archivo no permitido")
    if not os.path.isfile(target):
        raise HTTPException(status_code=404, detail="PDF no encontrado")
    return FileResponse(target, media_type="application/pdf", filename=safe_name)


@app.post("/chat")
def chat_route(payload: ChatRequest):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="El campo message es obligatorio")

    try:
        initialize_runtime()
    except Exception as exc:
        log.error("Error inicializando runtime: %s", exc)
        raise HTTPException(status_code=500, detail="Error iniciando el orquestador")

    history = normalizar_historial(payload.history)
    sesion = SesionChat(historial=history)

    try:
        respuesta = procesar_mensaje(payload.message.strip(), api_global, sesion)
        return {"response": respuesta}
    except Exception as exc:
        log.error("Error procesando /chat: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno del orquestador")


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    import uvicorn
    initialize_runtime()
    uvicorn.run(app, host=HTTP_HOST, port=HTTP_PORT)