"""
Módulo de chat IA con Ollama.
Detección de intención, generación de respuestas y procesamiento de mensajes.
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field

import ollama
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("asistente")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-8k")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "90"))
OLLAMA_TIMEOUT_RETRIES = int(os.getenv("OLLAMA_TIMEOUT_RETRIES", "2"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.1"))
OLLAMA_SEED = int(os.getenv("OLLAMA_SEED", "42"))

_ollama = ollama.Client(host=OLLAMA_HOST, timeout=OLLAMA_TIMEOUT)


def _chat_ollama(prompt, num_ctx, output_format=None):
    """Envía un prompt a Ollama y obtiene la respuesta."""
    ultimo_error = None

    for intento in range(1 + OLLAMA_TIMEOUT_RETRIES):
        try:
            kwargs = {
                "model": OLLAMA_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "options": {
                    "num_ctx": num_ctx,
                    "num_predict": OLLAMA_NUM_PREDICT,
                    "temperature": OLLAMA_TEMPERATURE,
                    "top_p": OLLAMA_TOP_P,
                    "seed": OLLAMA_SEED,
                },
            }
            if output_format:
                kwargs["format"] = output_format

            respuesta = _ollama.chat(**kwargs)

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

        if intento < OLLAMA_TIMEOUT_RETRIES:
            time.sleep(1)

    raise RuntimeError("Ollama no respondió: " + str(ultimo_error))


def detectar_intencion(mensaje):
    """Detecta la intención del mensaje del usuario."""
    prompt = """

Analizá el mensaje del usuario y devolvé
ÚNICAMENTE JSON válido.

NO uses markdown.
NO expliques nada.

    def validar_intencion(valor):
        acciones_validas = {"buscar", "precio", "stock", "web", "conversacion"}
        if not isinstance(valor, dict):
            raise ValueError("La intención no es un objeto JSON")
        if valor.get("accion") not in acciones_validas:
            raise ValueError("Acción de intención inválida")
        if not isinstance(valor.get("consulta", ""), str):
            raise ValueError("Consulta de intención inválida")
        return valor

    try:
        return validar_intencion(json.loads(contenido))
    except (json.JSONDecodeError, ValueError):
  "accion": "buscar" | "precio" | "stock" | "web" | "conversacion",
  "consulta": "texto de búsqueda"
}

REGLAS IMPORTANTES:
                return validar_intencion(
                    json.loads(contenido[inicio:fin + 1])
                )
            except (json.JSONDecodeError, ValueError):

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
        contenido = _chat_ollama(prompt, num_ctx=OLLAMA_NUM_CTX, output_format="json")
    except RuntimeError as e:
        log.error("detectar_intencion: %s", e)
        return {"accion": "buscar", "consulta": mensaje}

    try:
        resultado = json.loads(contenido)
        acciones_validas = {"buscar", "precio", "stock", "web", "conversacion"}
        if not isinstance(resultado, dict):
            raise ValueError("La intención no es un objeto JSON")
        if resultado.get("accion") not in acciones_validas:
            raise ValueError("Acción de intención inválida")
        if not isinstance(resultado.get("consulta", ""), str):
            raise ValueError("Consulta de intención inválida")
        return resultado
    except json.JSONDecodeError:
        inicio = contenido.find("{")
        fin = contenido.rfind("}")

        if inicio != -1 and fin != -1:
            try:
                return json.loads(contenido[inicio:fin + 1])
            except Exception:
                pass

    return {"accion": "buscar", "consulta": mensaje}


def generar_respuesta(mensaje, resultado, historial):
    """Genera la respuesta final basada en los resultados."""
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

Si reconoces que te estan pidiendo un producto en plural (por ejemplo, gamepads en vez de gamepad, cables en vez de cable)
sacale la s al final (o el "es") antes de realizar la busqueda, para que el resultado sea más preciso. esto es OBLIGATORIO, no te lo saltees
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
        return _chat_ollama(prompt, num_ctx=OLLAMA_NUM_CTX)
    except RuntimeError as e:
        log.error("generar_respuesta: %s", e)
        return "Perdón, tuve un problema para generar la respuesta."


@dataclass
class SesionChat:
    """Representa una sesión de chat con historial de mensajes."""

    historial: list = field(default_factory=list)
    ultimos_productos: list = field(default_factory=list)

    def registrar_turno(self, mensaje, respuesta):
        """Registra un turno de conversación."""
        self.historial.append(f"Usuario: {mensaje}")
        self.historial.append(f"Asistente: {respuesta}")

        if len(self.historial) > 16:
            self.historial = self.historial[-16:]


PALABRAS_CONTEXTO = [
    "este", "esta", "ese", "esa", "el anterior", "la anterior",
    "cada uno", "cuanto sale", "cuanto cuesta", "precio"
]


def resolver_consulta_con_contexto(consulta, sesion):
    """Resuelve una consulta usando el contexto de mensajes anteriores."""
    # Importar aquí para evitar circular imports
    from .catalogo import normalizar

    consulta_normalizada = normalizar(consulta)

    necesita_contexto = any(
        p in consulta_normalizada for p in PALABRAS_CONTEXTO
    )

    if necesita_contexto and sesion.ultimos_productos:
        if len(sesion.ultimos_productos) == 1:
            return sesion.ultimos_productos[0]["nombre"]

    return consulta


def generar_respuesta_productos(mensaje, productos, accion):
    """Construye la respuesta comercial sin regenerar datos con el modelo."""
    if not productos:
        return "No encontré productos que coincidan exactamente con la consulta."

    lineas = []
    for producto in productos:
        lineas.extend([
            f"SKU: {producto.get('sku', '')}",
            f"Descripción: {producto.get('nombre', '')}",
            f"Valor: USD ${_formatear_numero(producto.get('precio_usd', 0))}",
            f"Stock MDP: {_formatear_entero(producto.get('stock_mdp', 0))} unidades",
            f"Stock CABA: {_formatear_entero(producto.get('stock_caba', 0))} unidades",
            "",
        ])

    return "\n".join(lineas).rstrip()


def _formatear_numero(valor):
    try:
        return f"{float(valor):,.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _formatear_entero(valor):
    try:
        return str(int(float(valor)))
    except (TypeError, ValueError):
        return "0"
