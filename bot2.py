from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timedelta
from difflib import SequenceMatcher

app = FastAPI(title="Chatbot Minerva", description="Asistente virtual del Centro de Formación Minerva")

class ChatRequest(BaseModel):
    usuario: str
    mensaje: str

# Estados de sesión
sessions: Dict[str, str] = {}
last_activity: Dict[str, datetime] = {}
TIMEOUT_MINUTES = 5


# ============================
#   UTIL: similitud / matching
# ============================

def ratio(a: str, b: str) -> float:
    """Ratio de similitud entre dos strings (0..1)."""
    return SequenceMatcher(None, a, b).ratio()

def best_intent_by_similarity(texto: str, grupos: Dict[str, list]):
    """
    Devuelve (estado, score, palabra_matcheada)
    - score en 0..1
    """
    texto = texto.lower().strip()
    best_estado = None
    best_score = 0.0
    best_keyword = None

    for estado, keywords in grupos.items():
        for kw in keywords:
            s = ratio(texto, kw)
            if s > best_score:
                best_score = s
                best_estado = estado
                best_keyword = kw

            # También considerar prefijo (útil para entradas cortas tipo 'enf', 'aux')
            if len(texto) >= 2 and kw.startswith(texto):
                # darle una puntuación alta por prefijo
                return estado, 0.95, kw

    return best_estado, best_score, best_keyword


# ============================
#   NLP + Reglas (fuzzy + prefijo + sugerencias)
# ============================

def detectar_intencion(texto: str) -> (str, float, str):
    """
    Detecta intención y devuelve (estado, score, matched_keyword)
    score:
      - >= 0.65 => aceptar automáticamente
      - 0.45 - 0.65 => sugerir (autocompletar)
      - < 0.45 => no hay intención clara
    """
    texto = texto.lower().strip()

    grupos = {
        "sociosanitario": [
            "sociosanitario", "sociosanitaria", "dependencia", "geriatria",
            "geriátrico", "instituciones", "sociosan", "mayores", "geriatría",
            "residencia"
        ],
        "administrativo": [
            "administrativo", "administrativa", "auxiliar administrativo",
            "auxiliar admin", "admin", "oficina", "gestión", "recepcion", "documentos"
        ],
        "enfermeria": [
            "enfermeria", "enfermería", "auxiliar de enfermeria",
            "auxiliar de enfermería", "sanitario", "sanitaria", "curaciones", "auxiliar"
        ],
        "cajero": [
            "cajero", "reponedor", "caja", "supermercado", "mercadona", "tienda"
        ],
        "general": [
            "todos los cursos", "todos", "general", "catálogo general", "catalogo general", "cursos", "ver cursos"
        ]
    }

    # 1) coincidencia de palabra clave dentro del texto (alta confianza)
    for estado, keywords in grupos.items():
        for kw in keywords:
            if kw in texto and len(kw) >= 3:
                return estado, 0.99, kw

    # 2) mejor intención por similitud / prefijo
    estado, score, matched = best_intent_by_similarity(texto, grupos)

    # Normalizar score si None
    if not estado:
        return None, 0.0, None

    return estado, score, matched


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
            "Escribe el nombre del área (p. ej. 'enfermería') o simplemente presiona cualquier tecla para ver el menú."
        ),
        # Opciones numéricas por compatibilidad si front las envía
        "opciones_map": {
            "1": "sociosanitario",
            "2": "administrativo",
            "3": "enfermeria",
            "4": "cajero",
            "5": "general"
        }
    },
    "sociosanitario": {
        "mensaje": (
            "📘 Catálogo sociosanitario:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-ATENCION-SOCIOSANITARIA-A-PERSONAS-DEPENDIENTES-EN-INSTITUCIONES-SOCIALES-.pdf' target='_blank'>"
            "Descargar catálogo sociosanitario</a>\n\n"
            "Escribe otro área o 'inicio' para volver al menú."
        )
    },
    "administrativo": {
        "mensaje": (
            "📘 Catálogo administrativo:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Auxiliar-administrativo-2.pdf' target='_blank'>Descargar catálogo administrativo</a>\n\n"
            "Escribe otro área o 'inicio' para volver al menú."
        )
    },
    "enfermeria": {
        "mensaje": (
            "📘 Catálogo auxiliar de enfermería:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/10/"
            "Catalogo-de-Auxiliar-de-enfermeria-y-socio-sanitario-.pdf' target='_blank'>"
            "Descargar catálogo auxiliar de enfermería</a>\n\n"
            "Escribe otro área o 'inicio' para volver al menú."
        )
    },
    "cajero": {
        "mensaje": (
            "📘 Catálogo cajero reponedor:\n"
            "<a href='https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Cajero-Reponedor-.pdf' target='_blank'>Descargar catálogo cajero reponedor</a>\n\n"
            "Escribe otro área o 'inicio' para volver al menú."
        )
    },
    "general": {
        "mensaje": (
            "📘 Listado de todos los cursos:\n"
            "<a href='https://www.formacionminerva.com/cursos/' target='_blank'>Ver todos los cursos</a>\n\n"
            "Escribe otro área o 'inicio' para volver al menú."
        )
    }
}


# ============================
#      Controlador del Bot
# ============================

@app.post("/chatbot")
def chatbot(request: ChatRequest):
    usuario = request.usuario
    mensaje_raw = (request.mensaje or "").strip()
    mensaje = mensaje_raw.lower()

    now = datetime.now()
    ultima = last_activity.get(usuario)

    # Timeout: reiniciar sesión si inactividad
    if ultima and now - ultima > timedelta(minutes=TIMEOUT_MINUTES):
        sessions[usuario] = "inicio"
        last_activity[usuario] = now
        return {"estado": "inicio", "respuesta": arbol["inicio"]["mensaje"]}

    last_activity[usuario] = now

    # Estado actual
    estado_actual = sessions.get(usuario, "inicio")

    # Forzar 'inicio'
    if mensaje == "inicio":
        sessions[usuario] = "inicio"
        return {"estado": "inicio", "respuesta": arbol["inicio"]["mensaje"]}

    # Detectar intención (fuzzy + prefijo + keyword)
    intent, score, matched_kw = detectar_intencion(mensaje)

    # Si estamos en inicio: comportamiento "presiona cualquier tecla para ver menú"
    if estado_actual == "inicio":
        # 1) Si hay intención y es fuerte (score >= 0.65) -> ir directo
        if intent and score >= 0.65:
            sessions[usuario] = intent
            return {"estado": intent, "respuesta": arbol[intent]["mensaje"]}

        # 2) Si hay intención moderada (0.45 <= score < 0.65) -> SUGERIR (autocompletar)
        if intent and 0.45 <= score < 0.65:
            # Sugerir
            sugerencia = intent
            return {
                "estado": "inicio",
                "respuesta": (
                    f"🔍 ¿Quisiste decir: *{sugerencia}*?\n"
                    f"Si es así, escribe: '{sugerencia}' o simplemente confirma respondiendo 'sí'.\n\n"
                    + arbol["inicio"]["mensaje"]
                )
            }

        # 3) Si no hay intención clara: SI el usuario solo envió una tecla corta (por ejemplo 'g' o 'f'),
        #    o cualquier texto no reconocido, mostramos el menú (NO "No te entendí")
        #    excepto si el texto es claramente una petición vacía o comando inválido.
        #    Esto satisface la petición "presiona cualquier tecla para comenzar".
        if not intent:
            # Compatibilidad: si el frontend envía '1'..'5' también se acepta aquí
            opciones_map = arbol["inicio"].get("opciones_map", {})
            if mensaje in opciones_map:
                destino = opciones_map[mensaje]
                sessions[usuario] = destino
                return {"estado": destino, "respuesta": arbol[destino]["mensaje"]}
            # Mostrar menú
            return {"estado": "inicio", "respuesta": arbol["inicio"]["mensaje"]}

    # Si NO estamos en inicio:
    # - Si el usuario responde 'sí' tras una sugerencia previa (no mantenemos estado de sugerencia en memoria),
    #   pero podemos interpretar 'sí' junto con matched_kw: mejor no forzar, pedimos que escriba el nombre.
    if mensaje in ("si", "sí") and estado_actual == "inicio" and intent:
        # si llegamos aquí, aceptamos la intención detectada
        sessions[usuario] = intent
        return {"estado": intent, "respuesta": arbol[intent]["mensaje"]}

    # Fuera de inicio: si hay intención fuerte -> ir al catálogo
    if intent and score >= 0.65:
        sessions[usuario] = intent
        return {"estado": intent, "respuesta": arbol[intent]["mensaje"]}

    # Soporte entradas numéricas en otros estados (compatibilidad)
    opciones_map_global = arbol["inicio"].get("opciones_map", {})
    if mensaje in opciones_map_global:
        destino = opciones_map_global[mensaje]
        sessions[usuario] = destino
        return {"estado": destino, "respuesta": arbol[destino]["mensaje"]}

    # Si no entendimos fuera de inicio -> mostrar ayuda específica y menú del estado actual
    return {
        "estado": estado_actual,
        "respuesta": (
            "❓ No entendí tu respuesta.\n"
            "Puedes escribir, por ejemplo:\n"
            "- 'catálogo administrativo'\n"
            "- 'curso de enfermería'\n"
            "- 'sociosanitario'\n"
            "- 'ver todos los cursos'\n\n"
            + arbol.get(estado_actual, arbol["inicio"])["mensaje"]
        )
    }


