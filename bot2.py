from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Dict

app = FastAPI(title="Chatbot Minerva", description="Asistente virtual del Centro de Formación Minerva")

class ChatRequest(BaseModel):
    usuario: str
    mensaje: str

sessions: Dict[str, str] = {}

# Catálogos (solo URL, nada de descargas directas en backend)
catalogos_pdf = {
    "sociosanitario": "https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-ATENCION-SOCIOSANITARIA-A-PERSONAS-DEPENDIENTES-EN-INSTITUCIONES-SOCIALES-.pdf",
    "administrativo": "https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-Auxiliar-administrativo-2.pdf",
    "enfermeria": "https://www.formacionminerva.com/wp-content/uploads/2024/12/CATALOGO-NUEVO-CURSO-AUXILIAR-DE-ENFERMERIA-1-1.pdf",
    "cajero": "https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-Cajero-Reponedor-.pdf"
}

# Árbol conversacional (igual que antes)
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
        "opciones": {"1": "sociosanitario", "2": "administrativo", "3": "enfermeria", "4": "cajero", "5": "general"}
    },
    "sociosanitario": {
        "mensaje": (
            "Has elegido el área *Sociosanitaria* 🏥.\n"
            "1️⃣ Ver catálogo\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {"1": "sociosanitario_info", "2": "inicio"}
    },
    "sociosanitario_info": {
        "mensaje": (
            "📘 Catálogo sociosanitario:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-ATENCION-SOCIOSANITARIA-A-PERSONAS-DEPENDIENTES-EN-INSTITUCIONES-SOCIALES-.pdf\n\n"
            "📥 Descargar PDF directamente (redirección): /descargar_pdf?area=sociosanitario\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {"sí": "inicio", "si": "inicio", "no": "fin"}
    },
    "administrativo": {
        "mensaje": (
            "Has elegido el área *Administrativa* 💼.\n"
            "1️⃣ Ver catálogo\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {"1": "administrativo_info", "2": "inicio"}
    },
    "administrativo_info": {
        "mensaje": (
            "📘 Catálogo administrativo:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-Auxiliar-administrativo-2.pdf\n\n"
            "📥 Descargar PDF: /descargar_pdf?area=administrativo\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {"sí": "inicio", "si": "inicio", "no": "fin"}
    },
    "enfermeria": {
        "mensaje": (
            "Área *Auxiliar de enfermería* 👩‍⚕️.\n"
            "1️⃣ Ver catálogo\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {"1": "enfermeria_info", "2": "inicio"}
    },
    "enfermeria_info": {
        "mensaje": (
            "📘 Catálogo de auxiliar de enfermería:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2024/12/CATALOGO-NUEVO-CURSO-AUXILIAR-DE-ENFERMERIA-1-1.pdf\n\n"
            "📥 Descargar PDF: /descargar_pdf?area=enfermeria\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {"sí": "inicio", "si": "inicio", "no": "fin"}
    },
    "cajero": {
        "mensaje": (
            "Área *Cajero reponedor* 🛒.\n"
            "1️⃣ Ver catálogo\n"
            "2️⃣ Volver al menú principal"
        ),
        "opciones": {"1": "cajero_info", "2": "inicio"}
    },
    "cajero_info": {
        "mensaje": (
            "📘 Catálogo de cajero reponedor:\n"
            "🔗 https://www.formacionminerva.com/wp-content/uploads/2025/05/Catalogo-de-Cajero-Reponedor-.pdf\n\n"
            "📥 Descargar PDF: /descargar_pdf?area=cajero\n\n"
            "¿Quieres ver otro área? (sí / no)"
        ),
        "opciones": {"sí": "inicio", "si": "inicio", "no": "fin"}
    },
    "general": {
        "mensaje": (
            "Aquí tienes todos nuestros cursos 🎓:\n"
            "🔗 https://www.formacionminerva.com/cursos/\n\n"
            "¿Quieres volver al menú principal? (sí / no)"
        ),
        "opciones": {"sí": "inicio", "si": "inicio", "no": "fin"}
    },
    "fin": {"mensaje": "¡Perfecto! 😊 Si necesitas más información, solo envíame un mensaje cuando quieras.", "opciones": {}}
}


@app.post("/chatbot")
def chatbot(request: ChatRequest):
    usuario = request.usuario
    mensaje = request.mensaje.strip().lower()

    estado_actual = sessions.get(usuario, "inicio")
    nodo = arbol.get(estado_actual, arbol["inicio"])

    if estado_actual == "inicio":
        siguiente_estado = nodo["opciones"].get(mensaje, "inicio")
        sessions[usuario] = siguiente_estado
        return {"estado": siguiente_estado, "respuesta": arbol[siguiente_estado]["mensaje"]}

    siguiente_estado = nodo["opciones"].get(mensaje)

    if not siguiente_estado:
        return {"estado": estado_actual, "respuesta": "❓ No entendí tu respuesta.\n" + nodo["mensaje"]}

    sessions[usuario] = siguiente_estado
    return {"estado": siguiente_estado, "respuesta": arbol[siguiente_estado]["mensaje"]}


# --- Ruta para redirigir al PDF (compatible con Vercel) ---
@app.get("/descargar_pdf")
def descargar_pdf(area: str):
    if area not in catalogos_pdf:
        return {"error": "Área inválida"}

    return RedirectResponse(url=catalogos_pdf[area])
