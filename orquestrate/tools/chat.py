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
    """Detecta la intención del usuario y retorna un JSON estructurado."""
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
        contenido = _chat_ollama(prompt, num_ctx=OLLAMA_NUM_CTX, output_format="json")
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
