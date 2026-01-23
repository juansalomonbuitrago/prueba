
from fastapi import FastAPI 
from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime, timedelta

app = FastAPI(title="Chatbot Minerva", description="Asistente virtual del Centro de Formación Minerva")

# Modelo de solicitud
class ChatRequest(BaseModel):
    usuario: str
    mensaje: str

# --- Estado temporal de la conversación (en producción usar Redis o BD) ---
sessions: Dict[str, str] = {}

# Registro de última actividad para timeout
last_activity: Dict[str, datetime] = {}
TIMEOUT_MINUTES = 5   # Puedes ajustar el tiempo de timeout aquí

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
            "1️⃣ Ver catálogo de curso\n"
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
            "[Descargar catálogo](https://www.formacionminerva.com/wp-content/uploads/2026/01/Brochure-Sociosanitario.pdf)"
            "\n¿Quieres ver otro área? (sí / no)"
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
            "📘Aquí tienes el catálogo de auxiliar administrativo:\n"
            "[Descargar catálogo](https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-Auxiliar-administrativo-2.pdf)"
            "\n¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {
            "sí": "inicio",
            "si": "inicio",
            "no": "fin"
        }
    },
    "enfermeria": {
        "mensaje": (
            "Has elegido el área *Auxiliar de enfermería* 👩‍⚕️.\n"
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
            "📘 Aquí tienes el catálogo  de auxiliar de enfermería:\n"
            "[Descargar catálogo](https://www.formacionminerva.com/wp-content/uploads/2025/10/Catalogo-de-Auxiliar-de-enfermeria-y-socio-sanitario-.pdf)"
              "\n¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {
            "sí": "inicio",
            "si": "inicio",
            "no": "fin"
        }
    },
    "cajero": {
        "mensaje": (
            "Has elegido *Cajero reponedor* 🛒.\n"
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
            "📘  Aquí tienes el catálogo de cajero reponedor:\n"
            "[Descargar catálogo](https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-Cajero-Reponedor-.pdf)"
            "\n¿Quieres ver otro área? (sí / no)"
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
            "[Descargar catálogo](https://www.formacionminerva.com/cursos/)"
            "\n¿Quieres volver al menú principal? (sí / no)"
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

    # --- Timeout automático ---
    now = datetime.now()
    ultima = last_activity.get(usuario)

    if ultima and now - ultima > timedelta(minutes=TIMEOUT_MINUTES):
        # Reiniciar sesión después del timeout
        sessions[usuario] = "inicio"
        last_activity[usuario] = now

        return {
            "estado": "inicio",
            "respuesta": (
                "⏳ La sesión había expirado por inactividad.\n\n"
                "Hola, Soy Minervabot! 👋\n"
                "Tu asistente virtual, estoy aquí para ofrecerle los siguientes cursos:\n"
                "Presiona cualquier tecla para comenzar!\n\n"
                + arbol["inicio"]["mensaje"]
            )
        }

    # Actualizamos la última actividad
    last_activity[usuario] = now

    # Estado actual del usuario (si no existe, va a inicio)
    estado_actual = sessions.get(usuario, "inicio")
    nodo = arbol.get(estado_actual, arbol["inicio"])

    # Si la sesión estaba en "fin", reiniciamos elegantemente y mostramos saludo
    if estado_actual == "fin":
        sessions[usuario] = "inicio"
        last_activity[usuario] = now
        return {
            "estado": "inicio",
            "respuesta": (
                "Hola, Soy Minervabot! 👋\n"
                "Tu asistente virtual, estoy aquí para ofrecerle los siguientes cursos:\n"
                "Presiona cualquier tecla para comenzar!\n\n"
                + arbol["inicio"]["mensaje"]
            )
        }

    # --- Cambio solicitado: si está en inicio, NO mostrar error ---
    if estado_actual == "inicio":
        # Si el usuario no elige una opción válida, se repite el menú sin error
        siguiente_estado = nodo["opciones"].get(mensaje)
        if not siguiente_estado:
            return {"estado": "inicio", "respuesta": nodo["mensaje"]}

        sessions[usuario] = siguiente_estado
        return {"estado": siguiente_estado, "respuesta": arbol[siguiente_estado]["mensaje"]}

        # Si el usuario presiona cualquier tecla, simplemente mostramos el menú
        #siguiente_estado = nodo["opciones"].get(mensaje, "inicio")
        #sessions[usuario] = siguiente_estado
        #return {"estado": siguiente_estado, "respuesta": arbol[siguiente_estado]["mensaje"]}

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

    # --- Restart elegante al llegar al estado "fin" ---
    if siguiente_estado == "fin":
        # Reseteamos la sesión inmediatamente después de mostrar el mensaje final
        sessions[usuario] = "inicio"
        last_activity[usuario] = now

        return {
            "estado": "inicio",
            "respuesta": (
                "Hola, Soy Minervabot! 👋\n"
                "Tu asistente virtual, estoy aquí para ofrecerle los siguientes cursos:\n"
                "Presiona cualquier tecla para comenzar!\n\n"
                + arbol["inicio"]["mensaje"]
            )
        }

    # Respuesta normal
    return {
        "estado": siguiente_estado,
        "respuesta": nuevo_nodo["mensaje"]
    }
