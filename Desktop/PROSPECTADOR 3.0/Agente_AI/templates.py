"""
Templates de mensajes del bot — SKY Eleven
==========================================
REGLAS DE ORO:
- Máximo 2 líneas por mensaje
- Sin emojis en exceso (máximo 1 por mensaje)
- Nunca suena a bot, siempre a Gerardo o su equipo
- Sin puntos suspensivos ni signos raros
- Si el prospecto habla informal, el bot también
"""

# ─── PRIMER MENSAJE (lo manda GERARDO manualmente) ───────────────────────────
# El bot NO manda esto. Es el template para VOS.
# Personalizá [negocio] y [resultado_similar] antes de enviar.

PRIMER_MENSAJE_TEMPLATE = """
Hola {contacto}, vi que tienen {negocio} en {ciudad}.

Hace poco hicimos algo similar para {rubro_similar} y les cambió bastante la llegada de clientes. ¿Te cuento cómo?

— Gerardo, SKY Eleven
"""

# Versiones alternativas del primer mensaje (rotá para no sonar repetitivo)
PRIMER_MENSAJE_V2 = """Hola {contacto} 👋 soy Gerardo de SKY Eleven

Vi {negocio} y me pareció que podríamos ayudarlos a conseguir más clientes. ¿Tenés 20 minutos esta semana?"""

PRIMER_MENSAJE_V3 = """Hola {contacto}, soy Gerardo

Trabajo con negocios como {negocio} ayudándolos a vender más por internet. ¿Les interesa que les cuente cómo?"""


# ─── FLUJO DEL BOT (después que el prospecto responde) ───────────────────────

ESTADOS = {

    # Prospecto responde positivo al primer mensaje
    "BIENVENIDA": [
        "Buenísimo {contacto}, antes de contarte todo agendame un momento así no perdemos el hilo. ¿Cuándo te queda mejor, esta semana o la próxima?",
        "Perfecto. Agendame primero para que no se nos pierda el contacto — ¿esta semana o la próxima te queda mejor?",
        "Genial. Para no perder el hilo agendamos primero, ¿mañana o pasado podés?",
    ],

    # Prospecto da disponibilidad
    "CONFIRMAR_HORARIO": [
        "Dale, anoto {dia} a las {hora}. Te mando recordatorio el día anterior. Mientras tanto contame: ¿cómo están consiguiendo clientes hoy?",
        "Perfecto, quedamos {dia} a las {hora}. Te aviso antes. Una cosa: ¿tienen página web o redes sociales actualmente?",
        "Anotado {dia} {hora}. Antes de la reunión contame un poco: ¿qué es lo que más les cuesta del negocio ahora mismo?",
    ],

    # Prospecto cuenta su problema
    "EXPLORAR_PROBLEMA": [
        "Entiendo. Eso lo vemos mucho. ¿Cuánto tiempo lleva así el negocio?",
        "Claro, eso tiene solución. ¿Están buscando más clientes nuevos o fidelizar los que ya tienen?",
        "Sí, es común. ¿El problema principal es que no te encuentran en internet o que te encuentran pero no te contactan?",
    ],

    # Profundizar el problema
    "PROFUNDIZAR": [
        "¿Y tienen presencia en Google actualmente, o solo en redes?",
        "¿Alguien del equipo maneja la parte digital o está todo en vos?",
        "¿Tuvieron web antes o nunca tuvieron?",
    ],

    # Prospecto pregunta el precio
    "PRECIO": [
        "Depende de lo que necesitás, pero para que tengas referencia: webs simples desde $250.000 ARS, y sistemas completos con automatizaciones desde USD 800. En la reunión te muestro ejemplos reales y vemos qué te conviene exactamente.",
        "Tenemos desde $250.000 ARS para algo puntual hasta proyectos más completos en dólares según la complejidad. El jueves te muestro casos reales y definimos qué tiene más sentido para tu negocio.",
        "Arrancan en $250k ARS y depende mucho de lo que necesitás. Mejor que te muestre lo que hicimos para negocios similares y ahí ves si aplica — ¿te parece?",
    ],

    # Prospecto dice que no tiene presupuesto / está caro
    "OBJECION_PRECIO": [
        "Entiendo, por eso tenemos opciones desde $250k. A veces con algo chico ya se nota la diferencia. ¿Querés que en la reunión veamos primero qué necesitás y después vemos números?",
        "No hay drama, arrancamos chico si hace falta. Lo importante es que en 20 minutos podés ver si tiene sentido o no, sin compromiso.",
    ],

    # Prospecto dice que no tiene tiempo
    "OBJECION_TIEMPO": [
        "Sin problema, son solo 20 minutos por Zoom desde donde estés. ¿La semana que viene te queda mejor?",
        "Entiendo, lo hacemos por videollamada en el horario que más te acomoda. ¿Mañana temprano o a la tarde?",
    ],

    # Prospecto no responde (seguimiento automático día 3)
    "SEGUIMIENTO_3D": [
        "Hola {contacto}, te sigo de SKY Eleven. ¿Pudiste ver lo que te mandé? Quería saber si te interesó.",
        "Hola {contacto}, Gerardo de SKY Eleven. ¿Tuviste oportunidad de leer el mensaje? Cuéntame.",
    ],

    # Seguimiento día 7
    "SEGUIMIENTO_7D": [
        "Hola {contacto}, último intento de mi parte. Si en algún momento necesitás ayuda con el tema digital de {negocio}, acá estamos. Suerte 🙌",
    ],

    # Confirmar reunión agendada (aviso a Gerardo)
    "ALERTA_GERARDO": """🗓 *REUNIÓN AGENDADA — SKY Eleven*

👤 *Prospecto:* {contacto}
🏢 *Negocio:* {negocio}
📅 *Cuando:* {dia} a las {hora}
📞 *Teléfono:* {telefono}
🌐 *Fuente:* {fuente}
⭐ *Score:* {score}/100

💬 *Resumen de la charla:*
{resumen}

🔗 Ver en CRM: {crm_link}""",

    # Recordatorio automático al prospecto (día anterior a la reunión)
    "RECORDATORIO_REUNION": [
        "Hola {contacto}, te recuerdo que mañana tenemos la reunión a las {hora}. ¿Seguimos en pie?",
        "Hola {contacto} 👋 mañana a las {hora} hablamos. Cualquier cosa me avisás.",
    ],

    # Prospecto confirma recordatorio
    "CONFIRMA_RECORDATORIO": [
        "Perfecto, nos vemos mañana. Cualquier cosa me escribís acá.",
    ],

    # Prospecto cancela o reprograma
    "REPROGRAMAR": [
        "Sin problema, ¿cuándo te queda mejor para reagendar?",
        "Dale, no hay drama. ¿Qué día te viene bien la semana que viene?",
    ],

    # Prospecto dice que no le interesa
    "NO_INTERESADO": [
        "Sin problema, gracias igual {contacto}. Si en algún momento cambia algo, ya sabés dónde encontrarnos 👋",
    ],
}


# ─── DETECCIÓN DE INTENCIÓN ───────────────────────────────────────────────────
# Palabras clave para detectar qué quiere decir el prospecto

INTENT_KEYWORDS = {
    "positivo": [
        "sí", "si", "dale", "claro", "obvio", "me interesa", "contame",
        "quiero saber", "buenisimo", "genial", "perfecto", "bárbaro", "copado",
        "cuándo", "cuando", "podemos", "adelante", "vamos"
    ],
    "precio": [
        "cuánto", "cuanto", "precio", "costo", "cuesta", "vale", "tarifa",
        "presupuesto", "cobran", "cobras", "valores", "plata", "usd", "dólares"
    ],
    "no_tiempo": [
        "no tengo tiempo", "estoy ocupado", "ahora no", "no puedo",
        "más adelante", "después", "luego", "cuando pueda"
    ],
    "no_interesa": [
        "no me interesa", "no gracias", "no necesito", "ya tengo",
        "no quiero", "paso", "no es para mí"
    ],
    "dia_hora": [
        "lunes", "martes", "miércoles", "miercoles", "jueves", "viernes",
        "mañana", "pasado", "semana", "mañana", "tarde", "mañana",
        "10", "11", "12", "14", "15", "16", "17", "18", "hs", "hrs", "horas"
    ],
    "problema_web": [
        "no tengo web", "sin web", "necesito web", "quiero web",
        "página", "pagina", "sitio", "google", "internet"
    ],
    "problema_clientes": [
        "clientes", "ventas", "vender", "conseguir", "más gente",
        "no llega nadie", "poca gente", "no llaman"
    ],
}
