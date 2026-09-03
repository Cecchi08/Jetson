"""
Módulo de API de Grupo Núcleo.
Autenticación y acceso al catálogo de productos.
"""

import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("asistente")

API_BASE = os.getenv("GN_API_BASE", "https://api.gruponucleosa.com")
GN_ID = int(os.getenv("GN_ID", "1163"))
USERNAME = os.getenv("GN_USERNAME", "")
PASSWORD = os.getenv("GN_PASSWORD", "")
REQUEST_TIMEOUT = float(os.getenv("GN_REQUEST_TIMEOUT", "20"))


class GrupoNucleoAPI:
    """Cliente para acceder a la API de Grupo Núcleo."""

    def __init__(self):
        self.token = None
        self.catalogo = []
        self.cotizacion = None

    def login(self):
        """Autentica el usuario y obtiene el token."""
        if not USERNAME or not PASSWORD:
            raise RuntimeError("Faltan GN_USERNAME o GN_PASSWORD")

        url = f"{API_BASE}/Authentication/Login"

        payload = {
            "id": GN_ID,
            "username": USERNAME,
            "password": PASSWORD
        }

        try:
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            log.info("LOGIN STATUS: %s", response.status_code)

            response.raise_for_status()

            self.token = response.text.strip().strip('"')

            log.info("Token obtenido correctamente.")

        except Exception as e:
            log.error("Error en login: %s", e)
            raise

    def _get_con_reintento(self, url):
        """Obtiene URL con reintentos de login si el token expira."""
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
        """Obtiene el catálogo completo de productos."""
        url = f"{API_BASE}/API_V1/GetCatalog"

        try:
            response = self._get_con_reintento(url)
            log.info("CATALOG STATUS: %s", response.status_code)

            response.raise_for_status()

            data = response.json()

            if isinstance(data, dict):
                self.catalogo = data.get("table", [])
            else:
                self.catalogo = data if isinstance(data, list) else []

            log.info("Catálogo obtenido: %s productos", len(self.catalogo))

        except Exception as e:
            log.error("Error obteniendo catálogo: %s", e)
            raise

    def obtener_cotizacion_usd(self):
        """Obtiene la cotización del dólar para Grupo Núcleo."""
        url = f"{API_BASE}/API_V1/GetUSDExchange"

        try:
            response = self._get_con_reintento(url)
            log.info("USD EXCHANGE STATUS: %s", response.status_code)

            response.raise_for_status()

            data = response.json()

            self.cotizacion = (
                data.get("cotizacionUSD")
                or data.get("usd_value")
                or data.get("dolar")
                or None
            )

            if self.cotizacion:
                log.info("Cotización USD: %s", self.cotizacion)
            else:
                log.warning("No se obtuvo cotización USD")

        except Exception as e:
            log.error("Error obteniendo cotización USD: %s", e)

        return self.cotizacion


def obtener_cotizacion_usd(api):
    """Helper para obtener cotización del dólar."""
    return api.obtener_cotizacion_usd()
