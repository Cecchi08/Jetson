"""
Paquete tools - Módulos de funcionalidad del asistente IA.

Contiene:
- api.py: Cliente de API de Grupo Núcleo
- catalogo.py: Búsqueda y lógica de catálogo
- pdf.py: Generación de PDFs
- chat.py: IA y procesamiento de mensajes
"""

from .api import GrupoNucleoAPI, obtener_cotizacion_usd
from .catalogo import (
    normalizar, tokens, canonizar_terminos, dividir_consultas_compuestas,   
    detectar_categoria_consulta, es_consulta_deportiva, es_consulta_ram,
    texto_producto, es_memoria_ram, es_memoria_sd, es_motherboard, es_cpu,
    es_gpu, es_almacenamiento, es_fuente, producto_pertenece_categoria,
    resumir_producto, buscar_productos
)
from .pdf import generar_pdf_productos
from .chat import (
    detectar_intencion, generar_respuesta, SesionChat,
    resolver_consulta_con_contexto
)

__all__ = [
    # API
    "GrupoNucleoAPI",
    "obtener_cotizacion_usd",
    # Catálogo
    "normalizar",
    "tokens",
    "canonizar_terminos",
    "dividir_consultas_compuestas",
    "detectar_categoria_consulta",
    "es_consulta_deportiva",
    "es_consulta_ram",
    "es_consulta_ram",
    "texto_producto",
    "es_memoria_ram",
    "es_memoria_sd",
    "es_motherboard",
    "es_cpu",
    "es_gpu",
    "es_almacenamiento",
    "es_fuente",
    "producto_pertenece_categoria",
    "resumir_producto",
    "buscar_productos",
    # PDF
    "generar_pdf_productos",
    # Chat
    "detectar_intencion",
    "generar_respuesta",
    "SesionChat",
    "resolver_consulta_con_contexto",
]
