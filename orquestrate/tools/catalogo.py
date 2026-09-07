"""
Módulo de búsqueda de productos y lógica de catálogo.

Incluye:

- Normalización de texto.
- Normalización simple de plurales.
- Tokenización.
- Detección de categorías.
- Detección de tipo de producto.
- Filtros específicos para CPU, GPU, RAM, etc.
- Filtro obligatorio mediante "solo".
- Búsqueda por relevancia.
- Eliminación de duplicados.

Por ahora NO utiliza los archivos Excel de categorías/subcategorías.
"""

import logging
import hashlib
import os
import re

log = logging.getLogger("asistente")
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "50"))


# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalizar(texto):
    """
    Normaliza texto:
    - minúsculas
    - elimina acentos
    - elimina caracteres especiales
    - convierte espacios repetidos en uno
    """

    if texto is None:
        return ""

    texto = str(texto).lower()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    texto = re.sub(r"[^a-z0-9]+", " ", texto)

    return " ".join(texto.split())


def normalizar_plural_palabra(palabra):
    """
    Normaliza plurales simples.

    Ejemplos:
        gamepads -> gamepad
        mochilas -> mochila
        notebooks -> notebook
        monitores -> monitor
    """

    palabra = palabra.strip()

    if len(palabra) <= 3:
        return palabra

    excepciones = {
        "pcs": "pc",
        "rams": "ram",
        "gpus": "gpu",
        "cpus": "cpu",
        "hdds": "hdd",
        "ssds": "ssd",
        "nvmes": "nvme",
        "mouses": "mouse",
        "teclados": "teclado",
        "monitores": "monitor",
        "notebooks": "notebook",
        "laptops": "laptop",
        "computadoras": "computadora",
        "procesadores": "procesador",
        "microprocesadores": "microprocesador",
        "gamepads": "gamepad",
        "joysticks": "joystick",
        "auriculares": "auricular",
        "parlantes": "parlante",
        "memorias": "memoria",
        "fuentes": "fuente",
        "motherboards": "motherboard",
        "placas": "placa",
        "discos": "disco",
        "gabinetes": "gabinete",
        "impresoras": "impresora",
        "webcams": "webcam",
        "camcorders": "camcorder",
    }

    if palabra in excepciones:
        return excepciones[palabra]

    # Plurales terminados en "es"
    if palabra.endswith("es") and len(palabra) > 4:
        base = palabra[:-2]

        if base.endswith(("s", "x", "z")):
            return palabra

        return base

    # Plurales normales terminados en "s"
    if palabra.endswith("s") and len(palabra) > 4:
        return palabra[:-1]

    return palabra


def canonizar_terminos(texto):
    """
    Normaliza texto y convierte palabras plurales
    a una forma singular simple.
    """

    texto = normalizar(texto)

    if not texto:
        return ""

    palabras = texto.split()

    palabras = [
        normalizar_plural_palabra(palabra)
        for palabra in palabras
    ]

    return " ".join(palabras)


def tokens(texto):
    """
    Divide el texto en palabras de 2+ caracteres.
    """

    return [
        palabra
        for palabra in canonizar_terminos(texto).split()
        if len(palabra) >= 2
    ]


# ============================================================
# CONSULTAS COMPUESTAS
# ============================================================

def dividir_consultas_compuestas(consulta):
    """
    Divide consultas compuestas.

    Ejemplos:
        mouse y teclado
        -> ["mouse", "teclado"]

        notebook, mouse
        -> ["notebook", "mouse"]
    """

    texto = normalizar(consulta)

    if not texto:
        return [""]

    partes = [
        parte.strip()
        for parte in re.split(
            r"\b(?:y|e|and|plus|mas)\b|[,/&]",
            texto,
        )
        if parte.strip()
    ]

    return partes if partes else [texto]


# ============================================================
# CONSULTA "SOLO"
# ============================================================

def consulta_es_solo(consulta):
    """
    Detecta si la consulta contiene la palabra "solo".

    IMPORTANTE:
    Se busca sobre el texto normalizado ORIGINAL.
    No se depende de que otra función haya conservado
    la palabra "solo".
    """

    if consulta is None:
        return False

    q = normalizar(consulta)

    resultado = re.search(
        r"\bsolo\b",
        q,
    ) is not None

    log.info(
        "Detección SOLO | consulta=%r | normalizada=%r | resultado=%s",
        consulta,
        q,
        resultado,
    )

    return resultado


def consulta_es_todo(consulta):
    """
    Detecta explícitamente consultas con "todo".

    Ejemplos:
        todo ryzen
        todos los ryzen
        quiero todo
    """

    if consulta is None:
        return False

    q = normalizar(consulta)

    return bool(
        re.search(
            r"\b(?:todo|todos|todas)\b",
            q,
        )
    )


def quitar_palabras_control(consulta):
    """
    Quita palabras de control que no representan productos.

    Ejemplo:
        "solo microprocesadores ryzen"
        ->
        "microprocesadores ryzen"
    """

    q = canonizar_terminos(consulta)

    q = re.sub(
        r"\b(?:solo|todos|todas|todo)\b",
        " ",
        q,
    )

    return " ".join(q.split())


# ============================================================
# DETECCIÓN DE CATEGORÍA
# ============================================================

def detectar_categoria_consulta(consulta):
    """
    Detecta la categoría general de la consulta.
    """

    q = canonizar_terminos(consulta)

    motherboard_palabras = [
        "motherboard",
        "mother",
        "placa madre",
        "placa base",
        "mainboard",
    ]

    if any(palabra in q for palabra in motherboard_palabras):
        return "motherboard"

    gpu_palabras = [
        "placa de video",
        "placa video",
        "gpu",
        "rtx",
        "gtx",
        "radeon",
        "rx",
        "geforce",
    ]

    if any(palabra in q for palabra in gpu_palabras):
        return "gpu"

    cpu_palabras = [
        "micro",
        "microprocesador",
        "procesador",
        "cpu",
        "ryzen",
        "core i3",
        "core i5",
        "core i7",
        "core i9",
        "core ultra",
        "intel",
    ]

    if any(palabra in q for palabra in cpu_palabras):
        return "cpu"

    ram_palabras = [
        "ram",
        "memoria ram",
        "memoria",
        "ddr3",
        "ddr4",
        "ddr5",
        "udimm",
        "sodimm",
    ]

    if any(palabra in q for palabra in ram_palabras):
        return "ram"

    almacenamiento_palabras = [
        "ssd",
        "nvme",
        "disco",
        "hdd",
        "m2",
        "almacenamiento",
    ]

    if any(palabra in q for palabra in almacenamiento_palabras):
        return "almacenamiento"

    fuente_palabras = [
        "fuente",
        "psu",
        "power supply",
    ]

    if any(palabra in q for palabra in fuente_palabras):
        return "fuente"

    return None


# ============================================================
# DETECCIÓN DE TIPO DE PRODUCTO
# ============================================================

def detectar_tipo_producto(consulta):
    """
    Detecta productos concretos.
    """

    q = canonizar_terminos(consulta)

    patrones = [
        (
            "pc",
            r"\b(?:pc|pcs|computadora|computadoras)\b",
        ),
        (
            "notebook",
            r"\b(?:notebook|laptop)\b",
        ),
        (
            "monitor",
            r"\bmonitor\b",
        ),
        (
            "teclado",
            r"\bteclado\b",
        ),
        (
            "mouse",
            r"\bmouse\b",
        ),
        (
            "gamepad",
            r"\bgamepad\b",
        ),
        (
            "joystick",
            r"\bjoystick\b",
        ),
        (
            "mochila",
            r"\bmochila\b",
        ),
        (
            "auricular",
            r"\bauricular\b",
        ),
        (
            "parlante",
            r"\bparlante\b",
        ),
        (
            "webcam",
            r"\bwebcam\b",
        ),
    ]

    for tipo, patron in patrones:
        if re.search(patron, q):
            return tipo

    return None


# ============================================================
# DETECCIÓN FAMILIA CPU
# ============================================================

def detectar_familia_cpu(consulta):
    """
    Detecta familia de procesador.
    """

    q = canonizar_terminos(consulta)

    patrones = [
        ("ryzen 9", r"\bryzen\s+9\b"),
        ("ryzen 7", r"\bryzen\s+7\b"),
        ("ryzen 5", r"\bryzen\s+5\b"),
        ("ryzen 3", r"\bryzen\s+3\b"),

        ("core ultra 9", r"\bcore\s+ultra\s+9\b"),
        ("core ultra 7", r"\bcore\s+ultra\s+7\b"),
        ("core ultra 5", r"\bcore\s+ultra\s+5\b"),
        ("core ultra 3", r"\bcore\s+ultra\s+3\b"),

        ("core i9", r"\bcore\s+i9\b"),
        ("core i7", r"\bcore\s+i7\b"),
        ("core i5", r"\bcore\s+i5\b"),
        ("core i3", r"\bcore\s+i3\b"),

        ("ryzen", r"\bryzen\b"),
        ("intel", r"\bintel\b"),
        ("amd", r"\bamd\b"),
    ]

    for familia, patron in patrones:
        if re.search(patron, q):
            return familia

    return None


# ============================================================
# DDR
# ============================================================

def detectar_ddr(consulta):
    q = canonizar_terminos(consulta)

    for ddr in ("ddr5", "ddr4", "ddr3"):
        if ddr in q:
            return ddr

    return None


# ============================================================
# SOCKET
# ============================================================

def detectar_socket(consulta):
    q = canonizar_terminos(consulta)

    if re.search(r"\bam5\b", q):
        return "am5"

    if re.search(r"\bam4\b", q):
        return "am4"

    if re.search(r"\blga\s*1700\b", q):
        return "lga1700"

    if re.search(r"\blga\s*1200\b", q):
        return "lga1200"

    return None


# ============================================================
# CONSULTAS ESPECIALES
# ============================================================

def es_consulta_deportiva(consulta):
    q = normalizar(consulta)

    palabras = [
        "juega",
        "partido",
        "vs",
        "versus",
        "fixture",
        "resultado",
        "torneo",
        "liga",
        "campeonato",
        "final",
        "semifinal",
        "proximo",
        "hoy",
    ]

    return any(
        re.search(rf"\b{re.escape(palabra)}\b", q)
        for palabra in palabras
    )


def es_consulta_ram(consulta):
    return detectar_categoria_consulta(consulta) == "ram"


# ============================================================
# TEXTO DE PRODUCTO
# ============================================================

def texto_producto(producto):
    """
    Obtiene todo el texto relevante del producto.
    """

    campos = [
        producto.get("categoria", ""),
        producto.get("subcategoria", ""),
        producto.get("item_desc_0", ""),
        producto.get("item_desc_1", ""),
        producto.get("marca", ""),
        producto.get("codigo", ""),
        producto.get("ean", ""),
        producto.get("partNumber", ""),
    ]

    texto = " ".join(
        str(x)
        for x in campos
        if x is not None
    )

    return canonizar_terminos(texto)


# ============================================================
# FILTROS DE CATEGORÍA
# ============================================================

def es_memoria_ram(producto):
    texto = texto_producto(producto)

    subcategoria = canonizar_terminos(
        producto.get("subcategoria", "")
    )

    if subcategoria == "memoria":
        return True

    patrones = [
        "udimm",
        "sodimm",
        "ddr3",
        "ddr4",
        "ddr5",
        "memoria ram",
    ]

    return any(p in texto for p in patrones)


def es_memoria_sd(producto):
    texto = texto_producto(producto)

    patrones = [
        "memoria sd",
        "memoria micro sd",
        "micro sd",
        "microsd",
        "sdxc",
        "sdhc",
        "tarjeta sd",
    ]

    return any(p in texto for p in patrones)


def es_motherboard(producto):
    texto = texto_producto(producto)

    categoria = canonizar_terminos(
        producto.get("categoria", "")
    )

    subcategoria = canonizar_terminos(
        producto.get("subcategoria", "")
    )

    patrones = [
        "motherboard",
        "mother board",
        "placa madre",
        "placa base",
        "mainboard",
    ]

    if any(p in texto for p in patrones):
        return True

    if "mother" in categoria:
        return True

    if "mother" in subcategoria:
        return True

    return False


def es_cpu(producto):
    """
    Detecta si realmente es un procesador (CPU).

    Ryzen/Intel por sí solos no convierten cualquier producto
    en CPU. Se exige además que el producto tenga indicadores
    de procesador/categoría CPU.
    """

    texto = texto_producto(producto)

    categoria = canonizar_terminos(
        producto.get("categoria", "")
    )

    subcategoria = canonizar_terminos(
        producto.get("subcategoria", "")
    )

    categoria_cpu = (
        "micro" in categoria
        or "procesador" in categoria
        or "cpu" in categoria
        or "micro" in subcategoria
        or "procesador" in subcategoria
        or "cpu" in subcategoria
    )

    nombre = canonizar_terminos(producto.get("item_desc_0", ""))
    producto_compuesto = (
        "notebook" in categoria
        or "laptop" in categoria
        or "comput" in categoria
        or "notebook" in subcategoria
        or "laptop" in subcategoria
        or "comput" in subcategoria
        or re.search(r"\b(?:notebook|laptop|pc)\b", nombre) is not None
    )

    patrones_cpu = [
        "procesador",
        "microprocesador",
        "cpu",
        "ryzen",
        "core i3",
        "core i5",
        "core i7",
        "core i9",
        "core ultra",
    ]

    if producto_compuesto:
        return False

    return categoria_cpu or any(
        re.search(rf"\b{re.escape(patron)}\b", texto)
        for patron in patrones_cpu
    )


def es_gpu(producto):
    texto = texto_producto(producto)
    categoria = canonizar_terminos(producto.get("categoria", ""))
    subcategoria = canonizar_terminos(producto.get("subcategoria", ""))

    patrones = [
        "placa de video",
        "placa video",
        "geforce",
        "rtx",
        "gtx",
        "radeon",
        "rx",
    ]

    return any(
        re.search(rf"\b{re.escape(patron)}\b", texto)
        for patron in patrones
    ) or "video" in categoria or "video" in subcategoria


def es_almacenamiento(producto):
    texto = texto_producto(producto)

    patrones = [
        "ssd",
        "nvme",
        "disco rigido",
        "disco duro",
        "hdd",
        "m2",
    ]

    return any(p in texto for p in patrones)


def es_fuente(producto):
    texto = texto_producto(producto)

    patrones = [
        "fuente",
        "power supply",
        "psu",
    ]

    return any(p in texto for p in patrones)


def producto_pertenece_categoria(producto, categoria):
    if categoria is None:
        return True

    if categoria == "ram":
        return (
            es_memoria_ram(producto)
            and not es_memoria_sd(producto)
        )

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
# FILTRO DE TIPO DE PRODUCTO
# ============================================================

def producto_es_tipo(producto, tipo):
    """
    Comprueba si un producto pertenece al tipo solicitado.
    """

    if tipo is None:
        return True

    nombre = canonizar_terminos(
        producto.get("item_desc_0", "")
    )

    descripcion = canonizar_terminos(
        producto.get("item_desc_1", "")
    )

    categoria = canonizar_terminos(
        producto.get("categoria", "")
    )

    subcategoria = canonizar_terminos(
        producto.get("subcategoria", "")
    )

    texto = texto_producto(producto)

    if tipo == "pc":
        es_computadora = (
            "comput" in categoria
            or "comput" in subcategoria
            or categoria == "pc"
            or subcategoria == "pc"
            or re.search(r"\bpc\b", nombre) is not None
            or "pc gamer" in nombre
            or "equipo gamer" in nombre
            or "todo en uno" in nombre
            or "all in one" in nombre
            or "desktop" in categoria
            or "desktop" in subcategoria
            or re.search(r"\bdesktop\b", nombre) is not None
            or "computadora" in nombre
        )

        palabras_accesorio = (
            "mochila", "funda", "bolso", "maletin", "soporte", "base",
            "cooler", "cargador", "mouse", "teclado", "pad",
            "estabilizador", "cable", "adaptador",
        )
        return es_computadora and not any(
            re.search(rf"\b{re.escape(palabra)}\b", nombre)
            for palabra in palabras_accesorio
        )

    if tipo == "notebook":
        es_notebook = (
            "notebook" in categoria
            or "notebook" in subcategoria
            or "laptop" in categoria
            or "laptop" in subcategoria
            or re.search(r"\bnotebook\b", nombre) is not None
            or re.search(r"\blaptop\b", nombre) is not None
        )

        palabras_accesorio = (
            "mochila", "funda", "bolso", "maletin", "soporte", "base",
            "cooler", "cargador", "mouse", "teclado", "pad",
            "estabilizador", "cable", "adaptador", "bateria externa",
        )
        es_accesorio = any(
            re.search(rf"\b{re.escape(palabra)}\b", nombre)
            for palabra in palabras_accesorio
        )

        return es_notebook and not es_accesorio

    if tipo == "monitor":
        return (
            "monitor" in categoria
            or "monitor" in subcategoria
            or "monitor" in nombre
        )

    if tipo == "teclado":
        return (
            "teclado" in categoria
            or "teclado" in subcategoria
            or "teclado" in nombre
        )

    if tipo == "mouse":
        return (
            "mouse" in categoria
            or "mouse" in subcategoria
            or "mouse" in nombre
        )

    if tipo == "gamepad":
        return (
            "gamepad" in categoria
            or "gamepad" in subcategoria
            or "gamepad" in nombre
            or "gamepad" in descripcion
            or "gamepad" in texto
        )

    if tipo == "joystick":
        return (
            "joystick" in categoria
            or "joystick" in subcategoria
            or "joystick" in nombre
            or "joystick" in descripcion
        )

    if tipo == "mochila":
        return (
            "mochila" in categoria
            or "mochila" in subcategoria
            or "mochila" in nombre
            or "mochila" in descripcion
        )

    if tipo == "auricular":
        return (
            "auricular" in categoria
            or "auricular" in subcategoria
            or "auricular" in nombre
            or "headset" in nombre
        )

    if tipo == "parlante":
        return (
            "parlante" in categoria
            or "parlante" in subcategoria
            or "parlante" in nombre
        )

    if tipo == "webcam":
        return (
            "webcam" in categoria
            or "webcam" in subcategoria
            or "webcam" in nombre
        )

    return True


# ============================================================
# RESUMEN DE PRODUCTO
# ============================================================

def resumir_producto(producto):
    """
    Resume un producto a los campos principales.
    """

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
        "stock_caba": producto.get("stock_caba", 0),
    }


# ============================================================
# FILTRO OBLIGATORIO DE FAMILIA CPU
# ============================================================

def producto_cumple_familia_cpu(producto, familia_cpu):
    """
    Verifica obligatoriamente la familia solicitada.

    Ejemplo:
        "solo microprocesadores ryzen"

    El producto debe:
        1. ser CPU
        2. contener Ryzen

    Una computadora Ryzen NO pasa.
    Un Intel NO pasa.
    """

    if familia_cpu is None:
        return True

    if not es_cpu(producto):
        return False

    texto = texto_producto(producto)

    patrones = {
        "ryzen": r"\bryzen\b",
        "ryzen 9": r"\bryzen\s+9\b",
        "ryzen 7": r"\bryzen\s+7\b",
        "ryzen 5": r"\bryzen\s+5\b",
        "ryzen 3": r"\bryzen\s+3\b",

        "intel": r"\bintel\b",
        "amd": r"\bamd\b",

        "core i9": r"\bcore\s+i9\b",
        "core i7": r"\bcore\s+i7\b",
        "core i5": r"\bcore\s+i5\b",
        "core i3": r"\bcore\s+i3\b",

        "core ultra 9": r"\bcore\s+ultra\s+9\b",
        "core ultra 7": r"\bcore\s+ultra\s+7\b",
        "core ultra 5": r"\bcore\s+ultra\s+5\b",
        "core ultra 3": r"\bcore\s+ultra\s+3\b",
    }

    patron = patrones.get(familia_cpu)

    if patron is None:
        return True

    return bool(re.search(patron, texto))


# ============================================================
# FILTRO DE TÉRMINOS OBLIGATORIOS
# ============================================================

# Palabras comunes que no aportan a la identificación del producto
palabras_excluidas = {
    "para",
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "con",
    "que",
    "quiero",
    "dame",
    "buscar",
    "busco",
    "necesito",
    "mostrame",
    "mostrar",
}

def producto_contiene_todos_los_terminos(producto, consulta):
    """
    En modo SOLO, todos los términos relevantes de la consulta
    deben aparecer realmente en el producto.

    Esto evita resultados como:

        solo mochilas notebook

    devolviendo una mochila que no tiene relación con notebook.
    """

    texto = texto_producto(producto)

    terminos = [
        token
        for token in tokens(consulta)
        if token not in palabras_excluidas
    ]

    for termino in terminos:
        if not re.search(
            rf"\b{re.escape(termino)}\b",
            texto,
        ):
            return False

    return True

def producto_coincide_exacto(consulta, catalogo):
    """
    Encuentra productos cuyo nombre coincide exactamente con los términos de la consulta.
    
    Cuando se usa "solo", se busca el producto cuyo nombre normalizado
    contenga exactamente los términos de la consulta (sin palabras de paraguas).
    """
    # Extraer términos de la consulta (sin palabras de paraguas)
    consulta_normalizada = normalizar(consulta)
    terminos = [token for token in tokens(consulta_normalizada) if token not in palabras_excluidas]
    
    # Buscar productos cuyo nombre coincida exactamente
    resultados = []
    for producto in catalogo:
        # Usar el nombre normalizado del producto
        nombre_normalizado = normalizar(producto.get("item_desc_0", ""))
        
        # Verificar si el nombre coincide con los términos de la consulta
        coincidencia = True
        for termino in terminos:
            if not re.search(rf"\b{re.escape(termino)}\b", nombre_normalizado):
                coincidencia = False
                break
        
        if coincidencia:
            resultados.append(producto)
    
    return resultados

# ============================================================
# BÚSQUEDA INTELIGENTE
# ============================================================

def _producto_en_stock(producto, stock):
    """Reutiliza la lógica actual de stock del proyecto."""
    if stock is None:
        return True

    stock_total = int(producto.get("stock_mdp", 0) or 0) + int(producto.get("stock_caba", 0) or 0)

    if stock is True:
        return stock_total > 0

    if stock is False:
        return stock_total == 0

    return True


def _producto_coincide_marca(producto, marca):
    if marca is None:
        return True

    marca_normalizada = normalizar(marca)
    if not marca_normalizada:
        return True

    marca_producto = normalizar(producto.get("marca", ""))
    nombre = normalizar(producto.get("item_desc_0", ""))
    descripcion = normalizar(producto.get("item_desc_1", ""))
    texto = f"{nombre} {descripcion} {marca_producto}".strip()

    if marca_producto and re.search(rf"\b{re.escape(marca_normalizada)}\b", marca_producto):
        return True

    if marca_normalizada and re.search(rf"\b{re.escape(marca_normalizada)}\b", texto):
        return True

    return False


def _limite_cantidad(cantidad):
    if cantidad is None:
        return MAX_SEARCH_RESULTS

    try:
        cantidad_int = int(cantidad)
    except (TypeError, ValueError):
        return MAX_SEARCH_RESULTS

    return max(1, cantidad_int)


def buscar_productos(consulta=None, catalogo=None, categoria=None, tipo=None, marca=None, familia=None, ddr=None, socket=None, cantidad=None, stock=True, solo=True):
    """Búsqueda determinística por filtros estructurados.

    Compatibilidad:
    - buscar_productos("monitor", catalogo)
    - buscar_productos(catalogo, categoria="cpu", tipo="pc")
    """
    if catalogo is None and isinstance(consulta, list):
        catalogo = consulta
        consulta = None

    if catalogo is None:
        raise ValueError("catalogo es requerido")

    filtros_estructurados = any(
        valor is not None for valor in (categoria, tipo, marca, familia, ddr, socket)
    )

    if consulta is not None and isinstance(consulta, str) and not filtros_estructurados:
        return _buscar_productos_legacy(consulta, catalogo)

    if categoria is None and tipo is None and marca is None and familia is None and ddr is None and socket is None and consulta is None:
        return []

    resultados = []
    limite = _limite_cantidad(cantidad)

    for producto in catalogo:
        texto = texto_producto(producto)
        nombre = canonizar_terminos(producto.get("item_desc_0", ""))

        if categoria and not producto_pertenece_categoria(producto, categoria):
            continue

        if tipo and not producto_es_tipo(producto, tipo):
            continue

        if marca and not _producto_coincide_marca(producto, marca):
            continue

        if categoria == "cpu" and familia and not producto_cumple_familia_cpu(producto, familia):
            continue

        if ddr:
            ddr_busqueda = normalizar(ddr)
            if ddr_busqueda not in texto:
                continue

        if socket:
            socket_busqueda = normalizar(socket)
            socket_texto = normalizar(texto)
            if socket_busqueda not in socket_texto:
                continue

        if stock is not None and not _producto_en_stock(producto, stock):
            continue

        if tipo == "notebook" and producto_es_tipo(producto, "notebook"):
            accesorios = ["mochila", "funda", "bolso", "maletin", "soporte", "base", "cooler", "cargador", "mouse", "teclado", "pad", "estabilizador", "bateria externa"]
            if any(re.search(rf"\b{re.escape(p)}\b", nombre) for p in accesorios):
                continue

        score = 0

        if categoria and producto_pertenece_categoria(producto, categoria):
            score += 120

        if tipo and producto_es_tipo(producto, tipo):
            score += 120

        if marca and _producto_coincide_marca(producto, marca):
            score += 80

        if familia and categoria == "cpu" and producto_cumple_familia_cpu(producto, familia):
            score += 120

        if ddr and normalizar(ddr) in texto:
            score += 80

        if socket and normalizar(socket) in texto:
            score += 50

        if consulta is not None:
            q = canonizar_terminos(str(consulta))
            if q and q in nombre:
                score += 40
            if q and q in texto:
                score += 20
            for token in tokens(q):
                if re.search(rf"\b{re.escape(token)}\b", nombre):
                    score += 10
                if re.search(rf"\b{re.escape(token)}\b", texto):
                    score += 5

        if score <= 0:
            score = 1

        resultados.append((score, resumir_producto(producto)))

    resultados.sort(key=lambda item: item[0], reverse=True)

    vistos = set()
    productos_finales = []
    for _, producto in resultados:
        clave = (
            producto.get("item_id")
            or producto.get("codigo")
            or producto.get("partNumber")
            or hashlib.sha1(
                "|".join([
                    str(producto.get("nombre", "")),
                    str(producto.get("descripcion", "")),
                    str(producto.get("marca", "")),
                    str(producto.get("precio_usd", "")),
                ]).encode("utf-8")
            ).hexdigest()
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        productos_finales.append(producto)
        if len(productos_finales) >= limite:
            break

    return productos_finales


def _buscar_productos_legacy(consulta, catalogo):
    """Mantiene la lógica textual actual como fallback seguro."""
    consulta_original = str(consulta or "")
    es_solo = consulta_es_solo(consulta_original)
    es_todo = consulta_es_todo(consulta_original)
    partes_consulta = dividir_consultas_compuestas(consulta_original)

    if len(partes_consulta) > 1 and not es_solo:
        resultados_unidos = []
        vistos = set()
        for parte in partes_consulta:
            for producto in _buscar_productos_legacy(parte, catalogo):
                clave = producto.get("item_id") or producto.get("codigo") or producto.get("partNumber")
                if clave in vistos:
                    continue
                vistos.add(clave)
                resultados_unidos.append(producto)
        return resultados_unidos

    q_original = normalizar(consulta_original)
    q = canonizar_terminos(quitar_palabras_control(consulta_original))
    q_tokens = tokens(q)
    categoria_consulta = detectar_categoria_consulta(q)
    tipo_producto = detectar_tipo_producto(q)
    familia_cpu = detectar_familia_cpu(q)
    if categoria_consulta == "gpu":
        familia_cpu = None
    ddr_filtro = detectar_ddr(q)
    socket_filtro = detectar_socket(q)

    if es_solo:
        productos_exactos = producto_coincide_exacto(consulta_original, catalogo)
        productos_finales = []
        vistos = set()
        for producto in productos_exactos:
            identificador = producto.get("item_id") or producto.get("codigo") or producto.get("partNumber")
            if identificador in vistos:
                continue
            vistos.add(identificador)
            productos_finales.append(resumir_producto(producto))
        return productos_finales

    resultados = []
    for producto in catalogo:
        texto = texto_producto(producto)
        nombre = canonizar_terminos(producto.get("item_desc_0", ""))
        descripcion = canonizar_terminos(producto.get("item_desc_1", ""))
        marca = canonizar_terminos(producto.get("marca", ""))
        categoria = canonizar_terminos(producto.get("categoria", ""))
        subcategoria = canonizar_terminos(producto.get("subcategoria", ""))
        codigo = canonizar_terminos(producto.get("codigo", ""))
        ean = canonizar_terminos(producto.get("ean", ""))
        part_number = canonizar_terminos(producto.get("partNumber", ""))

        if categoria_consulta and not producto_pertenece_categoria(producto, categoria_consulta):
            continue

        if tipo_producto and not producto_es_tipo(producto, tipo_producto):
            continue

        if familia_cpu and not producto_cumple_familia_cpu(producto, familia_cpu):
            continue

        if ddr_filtro and not re.search(rf"\b{re.escape(ddr_filtro)}\b", texto):
            continue

        if socket_filtro and socket_filtro not in texto:
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
            if re.search(rf"\b{re.escape(token)}\b", nombre):
                score += 20
                encontrado = True
            if re.search(rf"\b{re.escape(token)}\b", descripcion):
                score += 8
                encontrado = True
            if re.search(rf"\b{re.escape(token)}\b", marca):
                score += 10
                encontrado = True
            if re.search(rf"\b{re.escape(token)}\b", categoria):
                score += 6
                encontrado = True
            if re.search(rf"\b{re.escape(token)}\b", subcategoria):
                score += 6
                encontrado = True
            if re.search(rf"\b{re.escape(token)}\b", part_number):
                score += 12
                encontrado = True
            if re.search(rf"\b{re.escape(token)}\b", codigo):
                score += 15
                encontrado = True
            if encontrado:
                tokens_encontrados += 1

        if categoria_consulta == "ram" and ddr_filtro:
            score += 70
        if tipo_producto:
            score += 100
        if familia_cpu:
            score += 150
        if socket_filtro:
            score += 50

        if q_tokens and len(q_tokens) >= 2:
            porcentaje = tokens_encontrados / len(q_tokens)
            if porcentaje < 0.75 and not es_solo:
                continue

        if score <= 0:
            continue

        resultados.append((score, producto))

    resultados.sort(key=lambda x: x[0], reverse=True)

    productos_finales = []
    vistos = set()
    for score, producto in resultados:
        identificador = producto.get("item_id") or producto.get("codigo") or producto.get("partNumber")
        if not identificador:
            identificador = hashlib.sha1(
                "|".join([
                    str(producto.get("item_desc_0", "")),
                    str(producto.get("item_desc_1", "")),
                    str(producto.get("marca", "")),
                    str(producto.get("precioNeto_USD", "")),
                ]).encode("utf-8")
            ).hexdigest()
        if identificador in vistos:
            continue
        vistos.add(identificador)
        productos_finales.append(resumir_producto(producto))
        if len(productos_finales) >= MAX_SEARCH_RESULTS:
            break

    return productos_finales