from fastapi import FastAPI 
from pydantic import BaseModel
from typing import Optional, Dict

app = FastAPI(title="Chatbot Minerva", description="Asistente virtual del Centro de Formación Minerva")

# Modelo de solicitud
class ChatRequest(BaseModel):
    usuario: str
    mensaje: str

# --- Estado temporal de la conversación (en producción usar Redis o BD) ---
sessions: Dict[str, str] = {}

# --- Definición del árbol conversacional ---
arbol = {
    "inicio": {
        "mensaje": (
            "Elige una de las siguientes opciones:\n"
            "1️⃣ Sociosanitario\n"
            "2️⃣ Administrativo\n"
            "3️⃣ Auxiliar de enfermería\n"
            "4️⃣ Cajero reponedor\n"
            "5️⃣ Ver todos los cursos"
        ),
        "opciones": {
            "1": "sociosanitario",
            "2": "administrativo",
            "3": "enfermeria",
            "4": "cajero",
            "5": "general"
        }
    },
    "sociosanitario": {
        "mensaje": (
            "Has elegido el área *Sociosanitaria* 🏥.\n"
            "¿Qué quieres hacer?\n"
            "1️⃣ Ver catálogo de cursos\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {
            "1": "sociosanitario_info",
            "2": "inicio"
        }
    },
    "sociosanitario_info": {
        "mensaje": (
            "📘 Aquí tienes el catálogo de formación sociosanitaria:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-ATENCION-SOCIOSANITARIA-A-PERSONAS-DEPENDIENTES-EN-INSTITUCIONES-SOCIALES-.pdf\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {
            "sí": "inicio",
            "si": "inicio",
            "no": "fin"
        }
    },
    "administrativo": {
        "mensaje": (
            "Has elegido el área *Administrativa* 💼.\n"
            "1️⃣ Ver catálogo\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {
            "1": "administrativo_info",
            "2": "inicio"
        }
    },
    "administrativo_info": {
        "mensaje": (
            "📘 Catálogo del área administrativa:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Auxiliar-administrativo-2.pdf\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {
            "sí": "inicio",
            "si": "inicio",
            "no": "fin"
        }
    },
    "enfermeria": {
        "mensaje": (
            "Área *Auxiliar de enfermería* 👩‍⚕️.\n"
            "1️⃣ Ver catálogo\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {
            "1": "enfermeria_info",
            "2": "inicio"
        }
    },
    "enfermeria_info": {
        "mensaje": (
            "📘 Catálogo del curso de auxiliar de enfermería:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2024/12/"
            "CATALOGO-NUEVO-CURSO-AUXILIAR-DE-ENFERMERIA-1-1.pdf\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {
            "sí": "inicio",
            "si": "inicio",
            "no": "fin"
        }
    },
    "cajero": {
        "mensaje": (
            "Área *Cajero reponedor* 🛒.\n"
            "1️⃣ Ver catálogo\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {
            "1": "cajero_info",
            "2": "inicio"
        }
    },
    "cajero_info": {
        "mensaje": (
            "📘 Catálogo del curso de cajero reponedor:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2025/05/"
            "Catalogo-de-Cajero-Reponedor-.pdf\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {
            "sí": "inicio",
            "si": "inicio",
            "no": "fin"
        }
    },
    "general": {
        "mensaje": (
            "Aquí tienes todos nuestros cursos disponibles 🎓:\n"
            "🔗 https://www.formacionminerva.com/cursos/\n\n"
            "¿Quieres volver al menú principal? (sí / no)"
        ),
        "opciones": {
            "sí": "inicio",
            "si": "inicio",
            "no": "fin"
        }
    },
    "fin": {
        "mensaje": "¡Perfecto! 😊 Si necesitas más información, solo envíame un mensaje cuando quieras.",
        "opciones": {}
    }
}


@app.post("/chatbot")
def chatbot(request: ChatRequest):
    usuario = request.usuario
    mensaje = request.mensaje.strip().lower()

    # Estado actual del usuario (si no existe, va a inicio)
    estado_actual = sessions.get(usuario, "inicio")
    nodo = arbol.get(estado_actual, arbol["inicio"])

    # --- Cambio solicitado: si está en inicio, NO mostrar error ---
    if estado_actual == "inicio":
        # Si el usuario presiona cualquier tecla, simplemente mostramos el menú
        siguiente_estado = nodo["opciones"].get(mensaje, "inicio")
        sessions[usuario] = siguiente_estado
        return {"estado": siguiente_estado, "respuesta": arbol[siguiente_estado]["mensaje"]}

    # Determinar siguiente estado normalmente
    siguiente_estado = None
    for clave, destino in nodo["opciones"].items():
        if mensaje == clave:
            siguiente_estado = destino
            break

    # Si no coincide, mostrar error (solo fuera de inicio)
    if not siguiente_estado:
        respuesta = (
            "❓ No entendí tu respuesta.\n"
            "Por favor elige una de las opciones válidas:\n"
            + nodo["mensaje"]
        )
        return {"estado": estado_actual, "respuesta": respuesta}

    # Actualizar sesión
    sessions[usuario] = siguiente_estado
    nuevo_nodo = arbol[siguiente_estado]

    return {
        "estado": siguiente_estado,
        "respuesta": nuevo_nodo["mensaje"]
    }