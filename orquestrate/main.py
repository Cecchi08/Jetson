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
import time
import os
import threading
from dataclasses import dataclass, field
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

import requests
import ollama
from bs4 import BeautifulSoup
import hashlib

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

OLLAMA_MODEL = "qwen2.5:14b-8k"

API_BASE = "https://api.gruponucleosa.com"

GN_ID = 1163
USERNAME = "pruebaapi"
PASSWORD = "123456789"

REQUEST_TIMEOUT = 20
OLLAMA_TIMEOUT_RETRIES = 2
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

HTTP_HOST = "0.0.0.0"
HTTP_PORT = int(os.getenv("HTTP_PORT", "9080"))

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

    def _send_json(self, status, payload):
        contenido = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(contenido)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/chat":
            self._send_json(404, {"error": "Recurso no encontrado"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length))
            mensaje = data.get("message", "").strip()

            if not mensaje:
                raise ValueError("message es requerido")

            inicio = time.time()

            respuesta = procesar_mensaje(
                mensaje,
                self.server.api,
                self.server.sesion
            )

            tiempo = time.time() - inicio

            log.info("POST /chat procesado en %.2f segundos", tiempo)

            self._send_json(200, {
                "response": respuesta
            })

        except json.JSONDecodeError:
            self._send_json(400, {"error": "JSON inválido"})
        except Exception as e:
            log.exception("Error en /chat")
            self._send_json(500, {"error": str(e)})

    def do_GET(self):

        # ----------------------------------------------------
        # HEALTH CHECK
        # ----------------------------------------------------

        if self.path == "/health":

            self._send_json(200, {"status": "ok"})
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
<style>
body {
    font-family: Arial, sans-serif;
    margin: 20px;
    background-color: #f5f5f5;
}
h1 {
    color: #333;
}
ul {
    list-style-type: none;
    padding: 0;
}
li {
    margin: 10px 0;
}
a {
    display: inline-block;
    padding: 10px 15px;
    background-color: #007bff;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    margin-right: 10px;
}
a:hover {
    background-color: #0056b3;
}
.download {
    background-color: #28a745;
}
.download:hover {
    background-color: #218838;
}
</style>
</head>
<body>
<h1>PDFs generados</h1>
<ul>
"""

                for archivo in archivos:

                    html += (
                        '<li>'
                        f'<a href="/pdfs/{archivo}" target="_blank">Ver PDF</a>'
                        f'<a href="/pdfs/{archivo}?download=true" class="download">Descargar</a>'
                        f'<span style="color:#666;">{archivo}</span>'
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

            # Separar el nombre del archivo del query string
            if "?" in self.path:
                ruta_path, query_string = self.path.split("?", 1)
                nombre = ruta_path[len("/pdfs/"):]
                descargar = "download=true" in query_string
            else:
                nombre = self.path[len("/pdfs/"):]
                descargar = False

            # Evitar salir de la carpeta
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
                
                # Si viene con ?download=true, forzar descarga. Si no, abrir en navegador
                if descargar:
                    self.send_header(
                        "Content-Disposition",
                        f'attachment; filename="{nombre}"'
                    )
                else:
                    self.send_header(
                        "Content-Disposition",
                        f'inline; filename="{nombre}"'
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

    def log_message(self, format, *args):

        log.info("HTTP: " + format, *args)


def iniciar_servidor_http(api, sesion):
    os.makedirs(PDF_FOLDER, exist_ok=True)

    servidor = ThreadingHTTPServer(
        (HTTP_HOST, HTTP_PORT),
        PDFRequestHandler
    )

    servidor.api = api
    servidor.sesion = sesion

    hilo = threading.Thread(
        target=servidor.serve_forever,
        daemon=True
    )
    hilo.start()

    log.info(
        "Servidor HTTP en http://%s:%s",
        HTTP_HOST,
        HTTP_PORT
    )

    return servidor


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
            "id": GN_ID,
            "username": USERNAME,
            "password": PASSWORD
        }

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)

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


def canonizar_terminos(texto):
    """Normaliza variantes plurales/singulares para que la misma consulta
    no cambie según la forma gramatical usada."""

    if texto is None:
        return ""

    texto = normalizar(texto)
    if not texto:
        return ""

    reemplazos = {
        "notebooks": "notebook",
        "laptops": "laptop",
        "monitores": "monitor",
        "teclados": "teclado",
        "mouses": "mouse",
        "pcs": "pc",
        "computadoras": "computadora",
        "computers": "computer",
        "rams": "ram",
        "gpus": "gpu",
        "fuentes": "fuente",
        "madres": "motherboard",
        "motherboards": "motherboard",
        "almacenamientos": "almacenamiento",
    }

    for plural, singular in reemplazos.items():
        texto = re.sub(rf"\b{plural}\b", singular, texto)

    return texto


def dividir_consultas_compuestas(consulta):

    texto = normalizar(consulta)
    if not texto:
        return [""]

    partes = [
        parte.strip()
        for parte in re.split(r"\b(?:y|e|and|plus|mas|,|/|&)\b", texto)
        if parte.strip()
    ]

    return partes if partes else [texto]


# ============================================================
# MAPEO DE CATEGORÍAS Y SUBCATEGORÍAS DESDE EXCEL
# ============================================================

MAPA_CATEGORIAS = {}
MAPA_SUBCATEGORIAS = {}
MAPA_CATEGORIAS_CARGADA = False


def _leer_hojas_xlsx(path):

    try:

        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(path) as archivo_zip:

            shared = archivo_zip.read("xl/sharedStrings.xml")
            root_shared = ET.fromstring(shared)
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            shared_strings = [
                nodo.find("a:t", ns).text
                for nodo in root_shared.findall(".//a:si", ns)
            ]

            sheet = ET.fromstring(archivo_zip.read("xl/worksheets/sheet1.xml"))

            filas = []
            for fila in sheet.findall(".//a:sheetData/a:row", ns):
                valores = []
                for celda in fila.findall("a:c", ns):
                    tipo = celda.attrib.get("t")
                    valor = celda.find("a:v", ns)
                    if valor is None:
                        valores.append("")
                        continue
                    texto = valor.text
                    if tipo == "s" and texto is not None:
                        try:
                            texto = shared_strings[int(texto)]
                        except (TypeError, ValueError, IndexError):
                            texto = ""
                    valores.append(texto or "")
                filas.append(valores)

            return filas

    except Exception as e:

        log.warning("No se pudo leer %s: %s", path, e)
        return []


def cargar_mapeos_categorias(force=False):

    global MAPA_CATEGORIAS, MAPA_SUBCATEGORIAS, MAPA_CATEGORIAS_CARGADA

    if MAPA_CATEGORIAS_CARGADA and not force:

        return {
            "categorias": MAPA_CATEGORIAS,
            "subcategorias": MAPA_SUBCATEGORIAS,
        }

    MAPA_CATEGORIAS = {}
    MAPA_SUBCATEGORIAS = {}

    base_dir = os.path.dirname(os.path.abspath(__file__))
    rutas = {
        "categorias": os.path.join(base_dir, "Categorias.xlsx"),
        "subcategorias": os.path.join(base_dir, "SubCategorias.xlsx"),
    }

    for nombre_archivo, ruta in rutas.items():

        if not os.path.exists(ruta):
            continue

        filas = _leer_hojas_xlsx(ruta)

        if nombre_archivo == "categorias":

            for fila in filas[1:]:

                if len(fila) < 2:
                    continue

                nombre = str(fila[0]).strip()
                categoria_id = str(fila[1]).strip()

                if not nombre or not categoria_id:
                    continue

                clave = normalizar(nombre)
                if clave:
                    try:
                        MAPA_CATEGORIAS[clave] = int(categoria_id)
                    except ValueError:
                        pass

        elif nombre_archivo == "subcategorias":

            for fila in filas[1:]:

                if len(fila) < 3:
                    continue

                nombre_categoria = str(fila[0]).strip()
                nombre_subcategoria = str(fila[1]).strip()
                id_raw = str(fila[2]).strip()

                if not nombre_categoria or not nombre_subcategoria or not id_raw:
                    continue

                if "|" in id_raw:
                    try:
                        subcategoria_id, categoria_id = [
                            int(x.strip()) for x in id_raw.split("|", 1)
                        ]
                    except ValueError:
                        continue
                else:
                    try:
                        subcategoria_id = int(id_raw)
                        categoria_id = MAPA_CATEGORIAS.get(
                            normalizar(nombre_categoria),
                            None,
                        )
                    except ValueError:
                        continue

                for clave in [normalizar(nombre_categoria), normalizar(nombre_subcategoria)]:
                    if clave:
                        MAPA_SUBCATEGORIAS[clave] = {
                            "categoria_id": categoria_id,
                            "subcategoria_id": subcategoria_id,
                        }

    MAPA_CATEGORIAS_CARGADA = True

    return {
        "categorias": MAPA_CATEGORIAS,
        "subcategorias": MAPA_SUBCATEGORIAS,
    }


def ids_de_consulta(consulta):

    cargar_mapeos_categorias()

    partes = dividir_consultas_compuestas(consulta)

    if not partes:
        partes = [normalizar(consulta)]

    categoria_ids = set()
    subcategoria_ids = set()

    for parte in partes:

        texto_tokens = set(parte.split())

        for clave, categoria_id in MAPA_CATEGORIAS.items():

            if clave == parte or clave in parte or any(token in clave for token in texto_tokens):
                categoria_ids.add(categoria_id)

        for clave, valor in MAPA_SUBCATEGORIAS.items():

            if clave == parte or clave in parte or any(token in clave for token in texto_tokens):
                if valor.get("categoria_id") is not None:
                    categoria_ids.add(valor["categoria_id"])
                if valor.get("subcategoria_id") is not None:
                    subcategoria_ids.add(valor["subcategoria_id"])

    return {
        "categoria_ids": categoria_ids,
        "subcategoria_ids": subcategoria_ids,
    }


def ids_de_producto(producto):

    cargar_mapeos_categorias()

    categoria = normalizar(producto.get("categoria", ""))
    subcategoria = normalizar(producto.get("subcategoria", ""))

    categoria_id = MAPA_CATEGORIAS.get(categoria)
    subcategoria_id = None

    if categoria_id is not None:
        subcategoria_id = MAPA_SUBCATEGORIAS.get(subcategoria, {}).get("subcategoria_id")

    if subcategoria_id is None:
        subcategoria_id = MAPA_SUBCATEGORIAS.get(categoria, {}).get("subcategoria_id")

    if categoria_id is None:
        categoria_id = MAPA_SUBCATEGORIAS.get(categoria, {}).get("categoria_id")

    return {
        "categoria_id": categoria_id,
        "subcategoria_id": subcategoria_id,
    }


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

    partes_consulta = dividir_consultas_compuestas(consulta)

    if len(partes_consulta) > 1:

        resultados_unidos = []
        vistos = set()

        for parte in partes_consulta:

            for producto in buscar_productos(parte, catalogo):

                clave = (
                    producto.get("item_id")
                    or producto.get("codigo")
                    or producto.get("partNumber")
                )

                if clave in vistos:
                    continue

                vistos.add(clave)
                resultados_unidos.append(producto)

        return resultados_unidos

    q = canonizar_terminos(consulta)
    q_tokens = tokens(q)
    categoria_ids_consulta = ids_de_consulta(consulta)

    # ========================================================
    # DETECTAR CATEGORÍA GENERAL
    # ========================================================

    categoria_consulta = detectar_categoria_consulta(consulta)

    # ========================================================
    # DETECTAR TIPO DE PRODUCTO
    # ========================================================

    tipo_producto = None

    if len(partes_consulta) > 1:
        tipo_producto = None

    # PC / COMPUTADORA
    if re.search(
        r"\bpc\b|\bpcs\b|\bcomputadora\b|\bcomputadoras\b",
        q
    ):
        tipo_producto = "pc"

    # NOTEBOOK
    elif re.search(
        r"\bnotebook\b|\bnotebooks\b|\blaptop\b|\blaptops\b",
        q
    ):
        tipo_producto = "notebook"

    # MONITOR
    elif re.search(
        r"\bmonitor\b|\bmonitores\b",
        q
    ):
        tipo_producto = "monitor"

    # TECLADO
    elif re.search(
        r"\bteclado\b|\bteclados\b",
        q
    ):
        tipo_producto = "teclado"

    # MOUSE
    elif re.search(
        r"\bmouse\b|\bmouses\b",
        q
    ):
        tipo_producto = "mouse"

    # ========================================================
    # DETECTAR FAMILIA DE CPU
    # ========================================================

    familia_cpu = None

    if re.search(r"\bryzen\s*9\b", q):
        familia_cpu = "ryzen 9"

    elif re.search(r"\bryzen\s*7\b", q):
        familia_cpu = "ryzen 7"

    elif re.search(r"\bryzen\s*5\b", q):
        familia_cpu = "ryzen 5"

    elif re.search(r"\bryzen\s*3\b", q):
        familia_cpu = "ryzen 3"

    elif re.search(r"\bcore\s*i9\b", q):
        familia_cpu = "core i9"

    elif re.search(r"\bcore\s*i7\b", q):
        familia_cpu = "core i7"

    elif re.search(r"\bcore\s*i5\b", q):
        familia_cpu = "core i5"

    elif re.search(r"\bcore\s*i3\b", q):
        familia_cpu = "core i3"

    elif re.search(r"\bcore\s*ultra\s*9\b", q):
        familia_cpu = "core ultra 9"

    elif re.search(r"\bcore\s*ultra\s*7\b", q):
        familia_cpu = "core ultra 7"

    elif re.search(r"\bcore\s*ultra\s*5\b", q):
        familia_cpu = "core ultra 5"

    elif re.search(r"\bcore\s*ultra\s*3\b", q):
        familia_cpu = "core ultra 3"

    elif re.search(r"\bintel\b", q):
        familia_cpu = "intel"

    elif re.search(r"\bamd\b", q):
        familia_cpu = "amd"

    # ========================================================
    # SI PIDE SOLO "RYZEN 5", "RYZEN 7", ETC.
    #
    # Se interpreta como MICRO.
    #
    # "Ryzen 5"          -> micros Ryzen 5
    # "Ryzen 7"          -> micros Ryzen 7
    # "Intel i5"         -> micros Intel i5
    #
    # En cambio:
    #
    # "PC Ryzen 5"       -> PCs Ryzen 5
    # "Notebook Ryzen 5" -> notebooks Ryzen 5
    # ========================================================

    if familia_cpu and tipo_producto is None:

        palabras_producto = [
            "pc",
            "pcs",
            "computadora",
            "computadoras",
            "notebook",
            "notebooks",
            "laptop",
            "laptops",
            "monitor",
            "monitores",
            "teclado",
            "teclados",
            "mouse",
            "mouses"
        ]

        tiene_tipo_producto = any(
            palabra in q
            for palabra in palabras_producto
        )

        if not tiene_tipo_producto:

            # Ryzen 5 / Ryzen 7 / Intel / etc.
            # => queremos CPUs
            categoria_consulta = "cpu"

    # ========================================================
    # DDR
    # ========================================================

    ddr_filtro = None

    if "ddr5" in q:
        ddr_filtro = "ddr5"

    elif "ddr4" in q:
        ddr_filtro = "ddr4"

    elif "ddr3" in q:
        ddr_filtro = "ddr3"

    # ========================================================
    # SOCKET
    # ========================================================

    socket_filtro = None

    if re.search(r"\bam5\b", q):
        socket_filtro = "am5"

    elif re.search(r"\bam4\b", q):
        socket_filtro = "am4"

    log.info(
        "Categoría: %s | Tipo: %s | CPU: %s | DDR: %s | Socket: %s",
        categoria_consulta,
        tipo_producto,
        familia_cpu,
        ddr_filtro,
        socket_filtro
    )

    # ========================================================
    # RECORRER CATÁLOGO
    # ========================================================

    resultados = []

    for producto in catalogo:

        texto = canonizar_terminos(texto_producto(producto))

        nombre = canonizar_terminos(
            producto.get("item_desc_0", "")
        )

        descripcion = canonizar_terminos(
            producto.get("item_desc_1", "")
        )

        marca = canonizar_terminos(
            producto.get("marca", "")
        )

        categoria = canonizar_terminos(
            producto.get("categoria", "")
        )

        subcategoria = canonizar_terminos(
            producto.get("subcategoria", "")
        )

        ids_producto = ids_de_producto(producto)

        codigo = normalizar(
            producto.get("codigo", "")
        )

        ean = normalizar(
            producto.get("ean", "")
        )

        part_number = normalizar(
            producto.get("partNumber", "")
        )

        # ====================================================
        # FILTRO CATEGORÍA TÉCNICA
        # ====================================================

        if categoria_ids_consulta["categoria_ids"] or categoria_ids_consulta["subcategoria_ids"]:
            producto_categoria_id = ids_producto.get("categoria_id")
            producto_subcategoria_id = ids_producto.get("subcategoria_id")

            if producto_categoria_id is not None and producto_categoria_id not in categoria_ids_consulta["categoria_ids"]:
                if producto_subcategoria_id is None or producto_subcategoria_id not in categoria_ids_consulta["subcategoria_ids"]:
                    continue

            if producto_subcategoria_id is not None and categoria_ids_consulta["subcategoria_ids"]:
                if producto_subcategoria_id not in categoria_ids_consulta["subcategoria_ids"]:
                    if producto_categoria_id is None or producto_categoria_id not in categoria_ids_consulta["categoria_ids"]:
                        continue

        if not producto_pertenece_categoria(
            producto,
            categoria_consulta
        ):
            continue

        # ====================================================
        # FILTRO PC
        # ====================================================

        if tipo_producto == "pc":

            # La categoría tiene que indicar computadora/PC.
            categoria_pc = (
                "comput" in categoria
                or "comput" in subcategoria
                or categoria == "pc"
                or subcategoria == "pc"
            )

            # Y además el producto tiene que ser realmente una PC.
            nombre_pc = (
                nombre.startswith("pc ")
                or " pc " in f" {nombre} "
                or "pcbox" in nombre
                or "pc gamer" in nombre
                or "equipo gamer" in nombre
                or "equipo todo en uno" in nombre
            )

            if not categoria_pc and not nombre_pc:
                continue

        # ====================================================
        # FILTRO NOTEBOOK
        # ====================================================

        elif tipo_producto == "notebook":

            # IMPORTANTE:
            # No alcanza con que el producto diga "notebook".
            # Una mochila para notebook también lo dice.
            #
            # Buscamos que la categoría/subcategoría sea
            # realmente informática/computación/notebook.

            categoria_notebook = (
                "comput" in categoria
                or "comput" in subcategoria
                or "notebook" in categoria
                or "notebook" in subcategoria
                or "laptop" in categoria
                or "laptop" in subcategoria
            )

            # El nombre tiene que ser de notebook/laptop.
            nombre_notebook = (
                nombre.startswith("notebook")
                or nombre.startswith("laptop")
                or " notebook " in f" {nombre} "
                or " laptop " in f" {nombre} "
            )

            # Evitar accesorios típicos
            accesorios_notebook = [
                "mochila",
                "funda",
                "bolso",
                "maletin",
                "maletin",
                "soporte",
                "base",
                "cooler",
                "cargador",
                "mouse",
                "teclado",
                "pad",
                "estabilizador"
            ]

            es_accesorio = any(
                palabra in nombre
                for palabra in accesorios_notebook
            )

            # Si es accesorio pero NO está categorizado como Notebooks, descartarlo
            if es_accesorio and not categoria_notebook:
                continue

            # Si no está en la categoría Notebooks, el nombre debe indicar notebook
            if not categoria_notebook and not nombre_notebook:
                continue

        # ====================================================
        # FILTRO MONITOR
        # ====================================================

        elif tipo_producto == "monitor":

            if "monitor" not in categoria and \
               "monitor" not in subcategoria and \
               "monitor" not in nombre:

                continue

        # ====================================================
        # FILTRO TECLADO
        # ====================================================

        elif tipo_producto == "teclado":

            if "teclado" not in categoria and \
               "teclado" not in subcategoria and \
               "teclado" not in nombre:

                continue

        # ====================================================
        # FILTRO MOUSE
        # ====================================================

        elif tipo_producto == "mouse":

            if "mouse" not in categoria and \
               "mouse" not in subcategoria and \
               "mouse" not in nombre:

                continue

        # ====================================================
        # FILTRO EXACTO DE FAMILIA CPU
        # ========================================================

        if familia_cpu:

            if familia_cpu == "ryzen 9":

                if not re.search(r"\bryzen\s*9\b", texto):
                    continue

            elif familia_cpu == "ryzen 7":

                if not re.search(r"\bryzen\s*7\b", texto):
                    continue

            elif familia_cpu == "ryzen 5":

                if not re.search(r"\bryzen\s*5\b", texto):
                    continue

            elif familia_cpu == "ryzen 3":

                if not re.search(r"\bryzen\s*3\b", texto):
                    continue

            elif familia_cpu == "core i9":

                if not re.search(r"\bcore\s*i9\b", texto):
                    continue

            elif familia_cpu == "core i7":

                if not re.search(r"\bcore\s*i7\b", texto):
                    continue

            elif familia_cpu == "core i5":

                if not re.search(r"\bcore\s*i5\b", texto):
                    continue

            elif familia_cpu == "core i3":

                if not re.search(r"\bcore\s*i3\b", texto):
                    continue

            elif familia_cpu == "core ultra 9":

                if not re.search(
                    r"\bcore\s*ultra\s*9\b",
                    texto
                ):
                    continue

            elif familia_cpu == "core ultra 7":

                if not re.search(
                    r"\bcore\s*ultra\s*7\b",
                    texto
                ):
                    continue

            elif familia_cpu == "core ultra 5":

                if not re.search(
                    r"\bcore\s*ultra\s*5\b",
                    texto
                ):
                    continue

            elif familia_cpu == "core ultra 3":

                if not re.search(
                    r"\bcore\s*ultra\s*3\b",
                    texto
                ):
                    continue

            elif familia_cpu == "intel":

                if "intel" not in texto:
                    continue

            elif familia_cpu == "amd":

                if "amd" not in texto:
                    continue

        # ====================================================
        # DDR
        # ====================================================

        if ddr_filtro:

            if ddr_filtro not in texto:
                continue

        # ====================================================
        # SOCKET
        # ====================================================

        if socket_filtro:

            if socket_filtro not in texto:
                continue

        # ====================================================
        # SCORE
        # ====================================================

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

        # ====================================================
        # TOKENS
        # ====================================================

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

        # ====================================================
        # BONUS
        # ====================================================

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

        if tipo_producto:
            score += 100

        if familia_cpu:
            score += 150

        if socket_filtro:
            score += 50

        # ====================================================
        # EVITAR RESULTADOS LEJANOS
        # ====================================================

        if q_tokens:

            porcentaje = (
                tokens_encontrados /
                len(q_tokens)
            )

            if len(q_tokens) >= 2 and porcentaje < 0.5:
                continue

        if score <= 0:
            continue

        resultados.append(
            (score, producto)
        )

    # ========================================================
    # ORDENAR
    # ========================================================

    resultados.sort(
        key=lambda x: x[0],
        reverse=True
    )

    # ========================================================
    # ELIMINAR DUPLICADOS
    # ========================================================

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

        productos_finales.append(
            resumir_producto(producto)
        )

    log.info(
        "Productos finales encontrados: %s",
        len(productos_finales)
    )

    return productos_finales# ============================================================
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

            cliente = ollama.Client(host=OLLAMA_HOST)

            respuesta = cliente.chat(
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
Devolvé ÚNICAMENTE JSON válido con esta forma:
{
  "accion": "buscar_productos",
  "categoria": null,
  "tipo": null,
  "marca": null,
  "familia": null,
  "ddr": null,
  "socket": null,
  "cantidad": 5,
  "stock": true,
  "solo": true
}

Reglas:
- accion: buscar_productos | precio | stock | web | conversacion
- categoria: cpu | gpu | ram | almacenamiento | fuente | motherboard | null
- tipo: pc | notebook | monitor | teclado | mouse | gamepad | joystick | mochila | auricular | parlante | webcam | null
- marca: nombre concreto, o null
- familia: Ryzen 5, Core i5, etc., o null
- ddr: DDR3 | DDR4 | DDR5 | null
- socket: AM4 | AM5 | LGA1700 | null
- cantidad: entero si lo pide el usuario; si no, usa null o un valor razonable
- stock: true | false | null
- solo: true cuando pide exclusivamente ese tipo/categoria

Ejemplos:
- "Dame 5 computadoras" -> {"accion":"buscar_productos","categoria":null,"tipo":"pc","marca":null,"familia":null,"ddr":null,"socket":null,"cantidad":5,"stock":true,"solo":true}
- "Dame 10 notebooks Lenovo" -> {"accion":"buscar_productos","categoria":null,"tipo":"notebook","marca":"Lenovo","familia":null,"ddr":null,"socket":null,"cantidad":10,"stock":true,"solo":true}
- "Dame 5 procesadores Ryzen 5" -> {"accion":"buscar_productos","categoria":"cpu","tipo":null,"marca":"AMD","familia":"Ryzen 5","ddr":null,"socket":null,"cantidad":5,"stock":true,"solo":true}
- "Dame procesadores Intel" -> {"accion":"buscar_productos","categoria":"cpu","tipo":null,"marca":"Intel","familia":null,"ddr":null,"socket":null,"cantidad":null,"stock":true,"solo":true}
- "Dame 3 memorias DDR5" -> {"accion":"buscar_productos","categoria":"ram","tipo":null,"marca":null,"familia":null,"ddr":"DDR5","socket":null,"cantidad":3,"stock":true,"solo":true}
- "hola" -> {"accion":"conversacion","categoria":null,"tipo":null,"marca":null,"familia":null,"ddr":null,"socket":null,"cantidad":null,"stock":null,"solo":true}

NO devuelvas texto fuera del JSON.
MENSAJE DEL USUARIO:
""" + mensaje

    try:
        contenido = _chat_ollama(prompt, num_ctx=8192)
    except RuntimeError as e:
        log.error("detectar_intencion: %s", e)
        return {
            "accion": "buscar_productos",
            "categoria": None,
            "tipo": None,
            "marca": None,
            "familia": None,
            "ddr": None,
            "socket": None,
            "cantidad": None,
            "stock": True,
            "solo": True,
        }

    try:
        resultado = json.loads(contenido)
        if not isinstance(resultado, dict):
            raise ValueError("La intención no es un objeto JSON")
        campos = ["accion", "categoria", "tipo", "marca", "familia", "ddr", "socket", "cantidad", "stock", "solo"]
        for campo in campos:
            if campo not in resultado:
                resultado[campo] = None if campo not in ("accion", "cantidad", "stock", "solo") else ("buscar_productos" if campo == "accion" else None if campo == "cantidad" else True if campo == "stock" else True)
        if resultado.get("accion") not in {"buscar_productos", "precio", "stock", "web", "conversacion"}:
            raise ValueError("Acción de intención inválida")
        if resultado.get("cantidad") is not None:
            try:
                resultado["cantidad"] = int(resultado["cantidad"])
            except (TypeError, ValueError):
                resultado["cantidad"] = None
        if resultado.get("stock") not in (True, False, None):
            resultado["stock"] = True
        if resultado.get("solo") not in (True, False):
            resultado["solo"] = True
        return resultado
    except (json.JSONDecodeError, ValueError):
        inicio = contenido.find("{")
        fin = contenido.rfind("}")
        if inicio != -1 and fin != -1:
            try:
                resultado = json.loads(contenido[inicio:fin + 1])
                if isinstance(resultado, dict):
                    return resultado
            except Exception:
                pass
        return {
            "accion": "buscar_productos",
            "categoria": None,
            "tipo": None,
            "marca": None,
            "familia": None,
            "ddr": None,
            "socket": None,
            "cantidad": None,
            "stock": True,
            "solo": True,
        }


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
    accion = intencion.get("accion", "buscar_productos")
    consulta = intencion.get("consulta", mensaje)

    log.info("Acción: %s | Consulta: %s | Intención: %s", accion, consulta, intencion)

    if accion == "conversacion":
        respuesta = generar_respuesta(mensaje, {}, sesion.historial)

    elif accion == "web":
        limite_web = 10 if es_consulta_deportiva(consulta) else 6
        resultados_web = buscar_web(consulta, limite=limite_web)
        datos = {"tipo": "busqueda_web", "consulta": consulta, "resultados": resultados_web}
        respuesta = generar_respuesta(mensaje, datos, sesion.historial)

    elif accion == "buscar_productos":
        consulta = resolver_consulta_con_contexto(consulta or mensaje, sesion)
        resultados = buscar_productos(
            api.catalogo,
            categoria=intencion.get("categoria"),
            tipo=intencion.get("tipo"),
            marca=intencion.get("marca"),
            familia=intencion.get("familia"),
            ddr=intencion.get("ddr"),
            socket=intencion.get("socket"),
            cantidad=intencion.get("cantidad"),
            stock=intencion.get("stock"),
            solo=intencion.get("solo", True),
            consulta=consulta,
        )
        sesion.ultimos_productos = resultados
        log.info("Buscador: %s resultados", len(resultados))

        pdf_generado = None
        if len(resultados) >= 3:
            log.info("Hay %s productos. Generando comparativa PDF...", len(resultados))
            pdf_generado = generar_pdf_productos(resultados, consulta, api.cotizacion)

        if pdf_generado:
            nombre_pdf = os.path.basename(pdf_generado)
            enlace_pdf = f"http://172.15.0.202:{HTTP_PORT}/pdfs/{nombre_pdf}"
            respuesta = (
                f"Encontré {len(resultados)} productos relevantes. "
                f"Podés ver la comparación completa aquí: {enlace_pdf}\n\n"
                + generar_respuesta(mensaje, {"productos": resultados}, sesion.historial)
            )
        else:
            respuesta = generar_respuesta(mensaje, {"productos": resultados}, sesion.historial)

    else:
        consulta = resolver_consulta_con_contexto(consulta or mensaje, sesion)
        resultados = buscar_productos(consulta, api.catalogo)
        sesion.ultimos_productos = resultados
        log.info("Buscador: %s resultados", len(resultados))

        pdf_generado = None
        if len(resultados) >= 3:
            log.info("Hay %s productos. Generando comparativa PDF...", len(resultados))
            pdf_generado = generar_pdf_productos(resultados, consulta, api.cotizacion)

        if pdf_generado:
            nombre_pdf = os.path.basename(pdf_generado)
            enlace_pdf = f"http://172.15.0.202:{HTTP_PORT}/pdfs/{nombre_pdf}"
            respuesta = (
                f"Encontré {len(resultados)} productos relevantes. "
                f"Podés ver la comparación completa aquí: {enlace_pdf}\n\n"
                + generar_respuesta(mensaje, {"productos": resultados}, sesion.historial)
            )
        else:
            respuesta = generar_respuesta(mensaje, {"productos": resultados}, sesion.historial)

        
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

def main():
    print("=" * 60)
    print("ASISTENTE IA - EMPRESA")
    print("=" * 60)
    print()
    print(f"Modelo: {OLLAMA_MODEL}")
    print(f"Ollama: {OLLAMA_HOST}")
    print(f"API: {API_BASE}")
    print(f"Puerto HTTP: {HTTP_PORT}")
    print()

    log.info("Inicializando conexión con Grupo Núcleo...")

    api = GrupoNucleoAPI()

    try:
        api.obtener_catalogo()
    except Exception as e:
        log.error("ERROR AL OBTENER EL CATÁLOGO: %s", e)
        return

    # ========================================================
    # COTIZACIÓN
    # ========================================================

    cotizacion = obtener_cotizacion_usd(api)
    api.cotizacion = cotizacion

    if cotizacion:
        print(f"Cotización USD: ${cotizacion}")
    else:
        print("Cotización USD: no disponible")

    # ========================================================
    # CREAR CARPETA DE PDFs
    # ========================================================

    os.makedirs(PDF_FOLDER, exist_ok=True)

    # ========================================================
    # SESIÓN
    # ========================================================

    sesion = SesionChat()

    # ========================================================
    # INICIAR SERVIDOR HTTP
    # ========================================================

    iniciar_servidor_http(api, sesion)

    print()
    print("=" * 60)
    print("ASISTENTE LISTO")
    print(f"Servidor HTTP: http://0.0.0.0:{HTTP_PORT}")
    print(f"Health: /health")
    print(f"Chat:   /chat")
    print(f"PDFs:   /pdfs/")
    print("=" * 60)
    print()

    # El contenedor debe permanecer ejecutándose.
    # El frontend se comunica mediante POST /chat.
    while True:
        time.sleep(3600)


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    main()

