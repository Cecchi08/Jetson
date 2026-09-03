"""
Asistente IA interno — Grupo Núcleo.
hola
Combina:
- API de Grupo Núcleo (catálogo de productos).
- Modelo local Ollama.
- Búsqueda web (DuckDuckGo HTML).
- Generación de PDFs comparativos (estilo institucional Grupo Núcleo).
- Servidor HTTP en puerto 9080 para ver/descargar PDFs.
"""

import json
import logging
import os
import threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

import requests
from bs4 import BeautifulSoup

# Importar todo de los módulos (el parche de hashlib está en tools/pdf.py)
from tools import (
    GrupoNucleoAPI,
    obtener_cotizacion_usd,
    normalizar,
    tokens,
    canonizar_terminos,
    dividir_consultas_compuestas,
    
    detectar_categoria_consulta,
  
    es_consulta_ram,
    texto_producto,
    es_memoria_ram,
    es_memoria_sd,
    es_motherboard,
    es_cpu,
    es_gpu,
    es_almacenamiento,
    es_fuente,
    producto_pertenece_categoria,
    resumir_producto,
    buscar_productos,
    generar_pdf_productos,
    detectar_intencion,
    generar_respuesta,
    generar_respuesta_productos,
    SesionChat,
    resolver_consulta_con_contexto,
)

# ============================================================
# CONFIGURACIÓN
# ============================================================

HTTP_HOST = "0.0.0.0"
HTTP_PORT = 9080
PDF_FOLDER = "pdf_generados"
MAX_PDF_PRODUCTS = int(os.getenv("MAX_PDF_PRODUCTS", "100"))

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

    def do_GET(self):

        # HEALTH CHECK
        if self.path == "/health":
            contenido = b'{"status":"ok"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(contenido)))
            self.end_headers()
            self.wfile.write(contenido)
            return

        # LISTADO DE PDFs
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

        # ARCHIVOS PDF
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
        """Suprime logs del servidor HTTP."""
        pass


def iniciar_servidor_http():
    """Inicia el servidor HTTP en background."""
    os.makedirs(PDF_FOLDER, exist_ok=True)

    servidor = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), PDFRequestHandler)

    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)

    hilo.start()

    log.info("Servidor HTTP en http://%s:%s", HTTP_HOST, HTTP_PORT)

    return servidor


# ============================================================
# BÚSQUEDA WEB
# ============================================================

def buscar_web(consulta, limite=10):
    """Busca información en web usando DuckDuckGo."""
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
# PROCESAR MENSAJE
# ============================================================

def procesar_mensaje(mensaje, api, sesion):
    """Procesa un mensaje del usuario y genera respuesta."""
    intencion = detectar_intencion(mensaje)

    accion = intencion.get("accion", "buscar")
    consulta = intencion.get("consulta", mensaje)

    log.info("Acción: %s | Consulta: %s", accion, consulta)

    # CONVERSACIÓN
    if accion == "conversacion":
        respuesta = generar_respuesta(mensaje, {}, sesion.historial)

    # WEB
    elif accion == "web":
        limite_web = 10 if es_consulta_deportiva(consulta) else 6
        resultados_web = buscar_web(consulta, limite=limite_web)

        datos = {
            "tipo": "busqueda_web",
            "consulta": consulta,
            "resultados": resultados_web
        }

        respuesta = generar_respuesta(mensaje, datos, sesion.historial)

    # CATÁLOGO
    else:
        consulta = resolver_consulta_con_contexto(consulta, sesion)
        resultados = buscar_productos(consulta, api.catalogo)
        sesion.ultimos_productos = resultados

        log.info("Buscador: %s resultados", len(resultados))

        # PDF
        pdf_generado = None

        if len(resultados) >= 3 and os.getenv("ENABLE_PRODUCT_PDF", "true").lower() == "true":
            log.info(
                "Hay %s productos. Generando comparativa PDF...",
                len(resultados)
            )

            productos_pdf = resultados[:MAX_PDF_PRODUCTS]
            pdf_generado = generar_pdf_productos(
                productos_pdf,
                consulta,
                api.cotizacion,
            )

        # RESPUESTA CON ENLACE AL PDF
        if pdf_generado:
            nombre_pdf = os.path.basename(pdf_generado)
            enlace_pdf = f"http://172.15.0.202:{HTTP_PORT}/pdfs/{nombre_pdf}"

            respuesta = (
                "Preparé una comparativa "
                f"con {len(productos_pdf)} productos.\n\n"
                "Podés descargarla acá:\n"
                f"{enlace_pdf}"
            )

        else:
            respuesta = generar_respuesta_productos(
                mensaje,
                resultados,
                accion,
            )

    # MEMORIA
    sesion.registrar_turno(mensaje, respuesta)

    return respuesta


# ============================================================
# MAIN
# ============================================================

def main():
    """Función principal del asistente."""
    log.info("Iniciando asistente IA — Grupo Núcleo")

    # Cargar API
    api = GrupoNucleoAPI()
    api.login()
    api.obtener_catalogo()

    # Obtener cotización
    obtener_cotizacion_usd(api)

    # Iniciar servidor HTTP
    iniciar_servidor_http()

    # Sesión de chat
    sesion = SesionChat()

    # Loop de conversación
    while True:
        try:
            mensaje = input("\nTú: ").strip()

            if not mensaje:
                continue

            if normalizar(mensaje) in ["salir", "exit", "quit"]:
                log.info("Terminando sesión.")
                break

            respuesta = procesar_mensaje(mensaje, api, sesion)

            print(f"\nAsistente:\n{respuesta}")

        except KeyboardInterrupt:
            log.info("Terminando sesión (Ctrl+C).")
            break

        except Exception as e:
            log.error("Error procesando mensaje: %s", e)
            print(f"Error: {e}")


if __name__ == "__main__":
    main()

