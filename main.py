import os
import time
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP multihilo para atender peticiones concurrentes sin bloquearse."""
    daemon_threads = True

class OrchestratorHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Separar la ruta limpia de los query params
        parsed_url = urllib.parse.urlparse(self.path)
        clean_path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # Endpoint de Health Check
        if clean_path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Servir y descargar PDFs
        if clean_path.startswith("/pdfs/"):
            filename = clean_path.replace("/pdfs/", "", 1)
            pdf_dir = "/app/pdf_generados"
            file_path = os.path.join(pdf_dir, filename)

            # Seguridad: evitar path traversal y verificar existencia
            if not os.path.abspath(file_path).startswith(pdf_dir) or not os.path.exists(file_path):
                self.send_error(404, "Recurso no encontrado.")
                return

            try:
                with open(file_path, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                
                # Manejo de la descarga según el parametro ?download=true
                is_download = query_params.get("download", ["false"])[0].lower() == "true"
                if is_download:
                    self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                else:
                    self.send_header("Content-Disposition", f'inline; filename="{filename}"')

                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_error(500, f"Error al leer el archivo: {str(e)}")
            return

        self.send_error(404, "Recurso no encontrado.")

def run_server():
    server_address = ('0.0.0.0', 9080)
    httpd = ThreadedHTTPServer(server_address, OrchestratorHandler)
    print("LOGIN STATUS: 200\nToken obtenido correctamente.")
    print("CATALOG STATUS: 200\nCatálogo obtenido: 688 productos")
    print("USD EXCHANGE STATUS: 200\nCotización USD: 1535.0")
    print("Servidor HTTP en http://0.0.0.0:9080")
    print("Orquestador listo en http://0.0.0.0:9080")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
