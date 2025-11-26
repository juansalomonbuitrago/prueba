
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
            "geriátrico", "instituciones", "sociosan", "mayores"
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
            "todos los cursos", "todos", "general", "catálogo general", "lista completa"
        ]
    }

    # Coincidencia exacta parcial
    for estado, palabras in grupos.items():
        for palabra in palabras:
            if palabra in texto:
                return estado

    # Fuzzy
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
        "enfermeria": ["enfermer", "sanitario", "aux enf"],
        "cajero": ["supermercado", "reponedor", "cajer"],
        "general": ["todos los cursos", "general"]
    }

    for estado, palabras in sugerencias.items():
        for palabra in palabras:
            if palabra in texto:
                return estado

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
            "Elige una opción o escríbeme qué curso buscas:\n"
            "• Sociosanitario 🏥\n"
            "• Administrativo 💼\n"
            "• Auxiliar de enfermería 👩‍⚕️\n"
            "• Cajero reponedor 🛒\n"
            "• Ver todos los cursos 🎓"
        ),
        "opciones": {}
    },
    "sociosanitario": {
        "mensaje": (
            "📘 Catálogo sociosanitario:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-ATENCION-SOCIOSANITARIA-A-PERSONAS-DEPENDIENTES-EN-INSTITUCIONES-SOCIALES-.pdf' target='_blank'>"
            "Descargar catálogo</a>\n\n"
            "¿Quieres ver otro curso?"
        )
    },
    "administrativo": {
        "mensaje": (
            "📘 Catálogo administrativo:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Auxiliar-administrativo-2.pdf' target='_blank'>Descargar catálogo</a>\n\n"
            "¿Quieres ver otro curso?"
        )
    },
    "enfermeria": {
        "mensaje": (
            "📘 Catálogo auxiliar de enfermería:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/10/"
            "Catalogo-de-Auxiliar-de-enfermeria-y-socio-sanitario-.pdf' target='_blank'>Descargar catálogo</a>\n\n"
            "¿Quieres ver otro curso?"
        )
    },
    "cajero": {
        "mensaje": (
            "📘 Catálogo cajero reponedor:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Cajero-Reponedor-.pdf' target='_blank'>Descargar catálogo</a>\n\n"
            "¿Quieres ver otro curso?"
        )
    },
    "general": {
        "mensaje": (
            "📘 Listado de todos los cursos:\n"
            "<a href='https://www.formacionminerva.com/cursos/' target='_blank'>Ver cursos</a>\n\n"
            "¿Quieres ver otro curso?"
        )
    }
}


# ============================
#      Controlador del Bot
# ============================

@app.post("/chatbot")
def chatbot(request: ChatRequest):
    usuario = request.usuario
    mensaje = request.mensaje.strip().lower()

    now = datetime.now()
    ultima = last_activity.get(usuario)

    if ultima and now - ultima > timedelta(minutes=TIMEOUT_MINUTES):
        sessions[usuario] = "inicio"
        last_activity[usuario] = now
        return {
            "estado": "inicio",
            "respuesta": "⏳ Sesión reiniciada por inactividad.\n\n" + arbol["inicio"]["mensaje"]
        }

    last_activity[usuario] = now

    estado_actual = sessions.get(usuario, "inicio")

    # NLP → identificar intención
    intencion = detectar_intencion(mensaje)
    auto = sugerir_autocompletado(mensaje)

    # Autocompletar estilo Google
    if not intencion and auto:
        return {
            "estado": estado_actual,
            "respuesta": f"🔍 ¿Quisiste decir <b>{auto}</b>?\n\n" + arbol["inicio"]["mensaje"]
        }

    # Si encontró intención → ir directo al catálogo
    if intencion:
        sessions[usuario] = intencion
        return {"estado": intencion, "respuesta": arbol[intencion]["mensaje"]}

    # Si no entendió nada → volver al menú
    return {
        "estado": "inicio",
        "respuesta": (
            "No te entendí 🤔, prueba escribiendo:\n"
            "- 'catálogo administrativo'\n"
            "- 'curso de enfermería'\n"
            "- 'sociosanitario'\n"
            "- 'todos los cursos'\n\n"
            + arbol["inicio"]["mensaje"]
        )
    }
