from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timedelta
import difflib

app = FastAPI(title="Chatbot Minerva", description="Asistente virtual del Centro de Formación Minerva")

class ChatRequest(BaseModel):
    usuario: str
    mensaje: str

# Estados de sesión
sessions: Dict[str, str] = {}
last_activity: Dict[str, datetime] = {}
TIMEOUT_MINUTES = 5


# ============================
#   NLP + Fuzzy Matching
# ============================

def fuzzy_match(texto, opciones, threshold=0.55):
    coincidencias = difflib.get_close_matches(texto, opciones, n=1, cutoff=threshold)
    return coincidencias[0] if coincidencias else None


def detectar_intencion(texto: str) -> str:
    texto = texto.lower()

    grupos = {
        "sociosanitario": [
            "sociosanitario", "sociosanitaria", "dependencia", "geriatria",
            "geriátrico", "instituciones", "sociosan", "mayores", "geriatría"
        ],
        "administrativo": [
            "administrativo", "administrativa", "auxiliar admin",
            "admin", "oficina", "gestión", "recepcion", "documentos"
        ],
        "enfermeria": [
            "enfermeria", "enfermería", "auxiliar de enfermeria",
            "auxiliar de enfermería", "sanitario", "sanitaria", "curaciones"
        ],
        "cajero": [
            "cajero", "reponedor", "caja", "supermercado", "mercadona", "tienda"
        ],
        "general": [
            "todos los cursos", "todos", "general", "catálogo general", "lista completa", "cursos"
        ]
    }

    # Coincidencia exacta parcial por presencia de palabra clave
    for estado, palabras in grupos.items():
        for palabra in palabras:
            if palabra in texto:
                return estado

    # Fuzzy match entre todas las palabras clave
    todas = []
    for lista in grupos.values():
        todas.extend(lista)

    coincidencia = fuzzy_match(texto, todas, threshold=0.5)
    if coincidencia:
        for estado, palabras in grupos.items():
            if coincidencia in palabras:
                return estado

    return None


def sugerir_autocompletado(texto: str):
    texto = texto.lower()

    sugerencias = {
        "sociosanitario": ["geriatria", "geriátrico", "instituciones", "mayores", "dependencia"],
        "administrativo": ["oficina", "admin", "auxiliar admin", "recepcion"],
        "enfermeria": ["enfermer", "sanitario", "aux enf", "curaciones"],
        "cajero": ["supermercado", "reponedor", "cajer"],
        "general": ["todos los cursos", "general", "cursos"]
    }

    # Búsqueda directa por palabras clave de sugerencia
    for estado, palabras in sugerencias.items():
        for palabra in palabras:
            if palabra in texto:
                return estado

    # Fuzzy sobre términos de sugerencia
    todas = []
    for lista in sugerencias.values():
        todas.extend(lista)

    coincidencia = fuzzy_match(texto, todas, threshold=0.5)
    if coincidencia:
        for estado, palabras in sugerencias.items():
            if coincidencia in palabras:
                return estado

    return None


# ============================
#      Árbol conversacional
# ============================

arbol = {
    "inicio": {
        "mensaje": (
            "Hola, Soy Minervabot! 👋\n"
            "Tu asistente virtual. Puedes escoger o escribir qué curso buscas:\n\n"
            "• Sociosanitario 🏥\n"
            "• Administrativo 💼\n"
            "• Auxiliar de enfermería 👩‍⚕️\n"
            "• Cajero reponedor 🛒\n"
            "• Ver todos los cursos 🎓\n\n"
            "Escribe el nombre del área o simplemente presiona cualquier tecla para ver el menú."
        ),
        "opciones": {}
    },
    "sociosanitario": {
        "mensaje": (
            "📘 Catálogo sociosanitario:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-ATENCION-SOCIOSANITARIA-A-PERSONAS-DEPENDIENTES-EN-INSTITUCIONES-SOCIALES-.pdf' target='_blank'>"
            "Descargar catálogo sociosanitario</a>\n\n"
            "¿Quieres ver otro curso? Escribe el nombre del área o 'inicio' para volver al menú."
        )
    },
    "administrativo": {
        "mensaje": (
            "📘 Catálogo administrativo:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Auxiliar-administrativo-2.pdf' target='_blank'>Descargar catálogo administrativo</a>\n\n"
            "¿Quieres ver otro curso? Escribe el nombre del área o 'inicio' para volver al menú."
        )
    },
    "enfermeria": {
        "mensaje": (
            "📘 Catálogo auxiliar de enfermería:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/10/"
            "Catalogo-de-Auxiliar-de-enfermeria-y-socio-sanitario-.pdf' target='_blank'>"
            "Descargar catálogo auxiliar de enfermería</a>\n\n"
            "¿Quieres ver otro curso? Escribe el nombre del área o 'inicio' para volver al menú."
        )
    },
    "cajero": {
        "mensaje": (
            "📘 Catálogo cajero reponedor:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Cajero-Reponedor-.pdf' target='_blank'>Descargar catálogo cajero reponedor</a>\n\n"
            "¿Quieres ver otro curso? Escribe el nombre del área o 'inicio' para volver al menú."
        )
    },
    "general": {
        "mensaje": (
            "📘 Listado de todos los cursos:\n"
            "<a href='https://www.formacionminerva.com/cursos/' target='_blank'>Ver todos los cursos</a>\n\n"
            "¿Quieres ver otro curso? Escribe el nombre del área o 'inicio' para volver al menú."
        )
    }
}


# ============================
#      Controlador del Bot
# ============================

@app.post("/chatbot")
def chatbot(request: ChatRequest):
    usuario = request.usuario
    mensaje = request.mensaje.strip()

    # Normalizar una versión en minúsculas para análisis
    mensaje_normalizado = mensaje.lower()

    now = datetime.now()
    ultima = last_activity.get(usuario)

    # Manejo de timeout
    if ultima and now - ultima > timedelta(minutes=TIMEOUT_MINUTES):
        sessions[usuario] = "inicio"
        last_activity[usuario] = now
        return {
            "estado": "inicio",
            "respuesta": arbol["inicio"]["mensaje"]
        }

    # Actualizamos la última actividad
    last_activity[usuario] = now

    # Estado actual
    estado_actual = sessions.get(usuario, "inicio")

    # Si el usuario escribe "inicio", forzamos volver al menú
    if mensaje_normalizado == "inicio":
        sessions[usuario] = "inicio"
        return {"estado": "inicio", "respuesta": arbol["inicio"]["mensaje"]}

    # Detectar intención y sugerencia
    intencion = detectar_intencion(mensaje_normalizado)
    auto = sugerir_autocompletado(mensaje_normalizado)

    # Si estamos en el estado inicial:
    if estado_actual == "inicio":
        # Si el usuario escribió una intención clara (incluso con errores), vamos directo
        if intencion:
            sessions[usuario] = intencion
            return {"estado": intencion, "respuesta": arbol[intencion]["mensaje"]}

        # Si no hay intención pero autocompletado sugiere algo, preguntamos al usuario
        if auto:
            # Sugerimos la opción, pero no rechazamos mostrar el menú si el usuario solo quiere ver opciones
            return {
                "estado": "inicio",
                "respuesta": (
                    f"🔍 ¿Quisiste decir: *{auto}*?\n"
                    f"Si es así, escribe: '{auto}' o simplemente presiona nuevamente la opción.\n\n"
                    + arbol["inicio"]["mensaje"]
                )
            }

        # Si no reconoce nada -> tratamos la entrada como "presionó cualquier tecla" y mostramos el menú
        # (Evita el mensaje "No te entendí" en el primer contacto)
        return {"estado": "inicio", "respuesta": arbol["inicio"]["mensaje"]}

    # Si no estamos en inicio:
    # - Primero, si detecta intención (p. ej. el usuario escribió "enfermeria"), redirigir
    if intencion:
        sessions[usuario] = intencion
        return {"estado": intencion, "respuesta": arbol[intencion]["mensaje"]}

    # - Si no, tratamos de mapear la entrada directa a un estado (por compatibilidad con entradas exactas)
    destino = None
    # comprobar nombres exactos de estados
    if mensaje_normalizado in arbol.keys():
        destino = mensaje_normalizado
    # comprobar por coincidencia con palabras clave de inicio (por si el frontend envía "1","2"...)
    else:
        # permitimos que if user sends '1' '2' etc. (compatibilidad)
        opciones_inicio_map = {
            "1": "sociosanitario",
            "2": "administrativo",
            "3": "enfermeria",
            "4": "cajero",
            "5": "general"
        }
        if mensaje_normalizado in opciones_inicio_map:
            destino = opciones_inicio_map[mensaje_normalizado]

    if destino:
        sessions[usuario] = destino
        return {"estado": destino, "respuesta": arbol[destino]["mensaje"]}

    # Si llegamos aquí, no entendimos fuera de inicio -> mensaje de ayuda + opciones actuales
    return {
        "estado": estado_actual,
        "respuesta": (
            "❓ No entendí tu respuesta.\n"
            "Puedes escribir algo como:\n"
            "- 'catálogo administrativo'\n"
            "- 'curso de enfermería'\n"
            "- 'sociosanitario'\n"
            "- 'ver todos los cursos'\n\n"
            + arbol.get(estado_actual, arbol["inicio"])["mensaje"]
        )
    }

