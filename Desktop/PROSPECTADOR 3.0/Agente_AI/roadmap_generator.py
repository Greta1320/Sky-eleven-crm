"""
Generador de Roadmaps de Venta — SKY Eleven
=============================================
Toma la info del cliente y genera un Roadmap personalizado
usando el prompt maestro del especialista.
"""

PROMPT_MAESTRO_ROADMAP = """
Eres un consultor senior de ventas B2B especializado en negocios locales latinoamericanos.
Tu trabajo es crear un ROADMAP DE VENTA completo y accionable para que un agente de IA 
pueda cerrar contratos con el cliente {nombre_empresa}.

DATOS DEL CLIENTE:
- Empresa: {nombre_empresa}
- Rubro: {rubro}
- Ciudad: {ciudad}
- Problema principal detectado: {problema_principal}
- Persona de contacto: {contacto}
- Tamaño estimado (chico/mediano/grande): {tamano}
- Presupuesto estimado: {presupuesto}
- Info adicional: {info_adicional}

INSTRUCCIONES:
Generá un roadmap de venta de 5 pasos con el siguiente formato EXACTO para cada paso:

PASO [N]: [NOMBRE DEL PASO]
OBJETIVO: [Qué queremos lograr en este paso]
MENSAJE: [El mensaje EXACTO que el bot debe enviar, personalizado para {nombre_empresa}]
SI RESPONDE SÍ: [Qué hacer/decir]
SI NO RESPONDE: [Qué hacer después de X días]
SEÑALES DE ALERTA: [Frases del cliente que indican que está listo para cerrar]

REGLAS IMPORTANTES:
- El Paso 1 es el primer WhatsApp en frío. Debe incluir el "gancho" específico del problema de {nombre_empresa}.
- El Paso 3 es donde se ofrece la demo o reunión.
- El Paso 5 es el cierre o descarte definitivo.
- Los mensajes deben ser naturales, NO de robot. Máximo 3 líneas por mensaje.
- Mencioná siempre el nombre del negocio para personalización.
- NO menciones precios hasta el Paso 4.
- El tono debe ser: {tono}

Al final del roadmap, generá una sección:
OBJECIONES FRECUENTES:
[Lista las 3 objeciones más comunes de este rubro y la respuesta exacta del bot]
"""

TONOS_POR_NICHO = {
    "autos": "directo, urgente, aspiracional. Hablar de éxito en ventas y showroom lleno.",
    "construccion": "serio, técnico, orientado a ROI. Hablar de proyectos y plazos.",
    "agencia_mkt": "moderno, orientado a datos, con vocabulario de marketing digital.",
    "restaurantes": "cálido, cercano. Hablar de reservas y más mesas ocupadas.",
    "clinicas": "profesional, confiable. Hablar de más pacientes y agenda completa.",
    "general": "amigable pero profesional. Enfocado en soluciones prácticas."
}


async def generar_roadmap(cliente_info: dict, api_key: str) -> dict:
    """
    Genera un roadmap personalizado para el cliente usando Claude AI.
    
    cliente_info debe tener:
    - nombre_empresa, rubro, ciudad, problema_principal,
      contacto, tamano, presupuesto, info_adicional
    """
    import anthropic
    import json

    nicho = cliente_info.get("nicho", "general")
    tono = TONOS_POR_NICHO.get(nicho, TONOS_POR_NICHO["general"])

    prompt = PROMPT_MAESTRO_ROADMAP.format(
        nombre_empresa    = cliente_info.get("nombre_empresa", "el cliente"),
        rubro             = cliente_info.get("rubro", "negocio local"),
        ciudad            = cliente_info.get("ciudad", ""),
        problema_principal= cliente_info.get("problema_principal", "sin presencia digital"),
        contacto          = cliente_info.get("contacto", "el dueño"),
        tamano            = cliente_info.get("tamano", "mediano"),
        presupuesto       = cliente_info.get("presupuesto", "a definir"),
        info_adicional    = cliente_info.get("info_adicional", "ninguna"),
        tono              = tono
    )

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    roadmap_texto = response.content[0].text

    return {
        "ok": True,
        "cliente": cliente_info.get("nombre_empresa"),
        "nicho": nicho,
        "roadmap": roadmap_texto,
        "fecha": __import__("datetime").datetime.now().isoformat()
    }
