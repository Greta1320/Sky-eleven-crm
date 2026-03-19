"""
Configuración central del Agente SKY Eleven
Edita este archivo para ajustar el comportamiento del agente
"""

import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # ─── NICHOS Y PERSONALIDAD ──────────────────────────────────
    ACTIVE_PERSONA: str  = os.getenv("ACTIVE_PERSONA", "general")
    AUTOPILOT_MODE: bool = os.getenv("AUTOPILOT_MODE", "False").lower() == "true"
    WSP_AUTO_REPLY: bool = os.getenv("WSP_AUTO_REPLY", "True").lower() == "true"

    # ─── CANALES DE PROSPECCIÓN ──────────────────────────────────
    CANALES_ACTIVOS: List[str] = field(default_factory=lambda: [
        "google_maps",
        "instagram",
        "linkedin"
    ])

    # ─── PARÁMETROS DE BÚSQUEDA ──────────────────────────────────
    CIUDADES: List[str] = field(default_factory=lambda: [
        "Ciudad de México",
        "Guadalajara",
        "Monterrey",
    ])
    CATEGORIAS: List[str] = field(default_factory=lambda: [
        "restaurantes",
        "clínicas dentales",
        "abogados",
        "spas",
        "constructoras",
        "academias",
        "tiendas ropa",
    ])
    SERVICIOS_OFRECIDOS: List[str] = field(default_factory=lambda: [
        "Web desde cero",
        "Rediseño web",
        "E-commerce",
        "Landing Page",
        "SEO",
    ])

    # ─── SCHEDULER ───────────────────────────────────────────────
    INTERVALO_HORAS: int = int(os.getenv("INTERVALO_HORAS", "6"))   # Cada cuántas horas corre
    DIAS_SEGUIMIENTO: int = int(os.getenv("DIAS_SEGUIMIENTO", "3")) # Días sin respuesta → seguimiento

    # ─── CALIFICACIÓN IA ─────────────────────────────────────────
    SCORE_MINIMO_WSP: int = int(os.getenv("SCORE_MINIMO_WSP", "70")) # Score mínimo para notificar por WA
    SCORE_MINIMO_EMAIL: int = int(os.getenv("SCORE_MINIMO_EMAIL", "50"))

    # ─── EVOLUTION API (WhatsApp) ─────────────────────────────────
    EVOLUTION_API_URL: str     = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
    EVOLUTION_API_KEY: str     = os.getenv("EVOLUTION_API_KEY", "")
    EVOLUTION_INSTANCE: str    = os.getenv("EVOLUTION_INSTANCE", "sky_eleven")
    WSP_NUMERO_DESTINO: str    = os.getenv("WSP_NUMERO_DESTINO", "")   # Tu número donde recibes alertas
    WSP_NUMERO_CLIENTE: bool   = bool(os.getenv("WSP_CONTACTAR_CLIENTE", False))  # Si también contacta al prospecto

    # ─── BASE DE DATOS (tu CRM existente) ─────────────────────────
    DB_TYPE: str    = os.getenv("DB_TYPE", "sqlite")       # "sqlite" o "postgres"
    DB_PATH: str    = os.getenv("DB_PATH", "crm.db")       # Solo para SQLite
    DB_HOST: str    = os.getenv("DB_HOST", "localhost")
    DB_PORT: int    = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str    = os.getenv("DB_NAME", "sky_crm")
    DB_USER: str    = os.getenv("DB_USER", "")
    DB_PASS: str    = os.getenv("DB_PASS", "")

    # ─── ANTHROPIC (Claude para calificación) ────────────────────
    ANTHROPIC_API_KEY: str     = os.getenv("ANTHROPIC_API_KEY", "")
    USAR_IA_CLAUDE: bool       = bool(os.getenv("USAR_IA_CLAUDE", True))

    # ─── BRANDING & SYNC ──────────────────────────────────────────
    AGENT_NAME: str   = os.getenv("AGENT_NAME", "Gerardo")
    COMPANY_NAME: str = os.getenv("COMPANY_NAME", "SKY Eleven")
    LICENSE_KEY: str  = os.getenv("LICENSE_KEY", "prospectos_ai_default")

    # ─── PLANTILLAS DE MENSAJE ────────────────────────────────────
    TEMPLATE_WSP_ALERTA: str = """🚀 *NUEVO PROSPECTO HOT — {company_name}*

🏢 *Negocio:* {nombre_negocio}
👤 *Contacto:* {contacto}
📍 *Ciudad:* {ciudad}
🌐 *Fuente:* {fuente}
⭐ *Score IA:* {score}/100
🛠️ *Servicio sugerido:* {servicio}

📞 *Teléfono:* {telefono}
📧 *Email:* {email}

💡 *Por qué es HOT:* {razon_score}
🔬 *Gancho Técnico:* {tecnico_hook}

🔗 Ver en CRM: {crm_link}"""

    TEMPLATE_EMAIL_PRIMER_CONTACTO: str = """Hola {contacto},

Noté que {nombre_negocio} está creciendo en {ciudad} y vi que aún no tienen una presencia web optimizada que les ayude a captar más clientes en Google.

En {company_name} ayudamos a negocios como el tuyo a conseguir más clientes con sitios web profesionales y estrategias digitales efectivas.

¿Podríamos hablar 15 minutos esta semana para contarte cómo podemos ayudarlos?

Saludos,
{agent_name} — {company_name}"""

    TEMPLATE_DM_INSTAGRAM: str = """Hola {contacto} 👋

Vi {nombre_negocio} en Instagram y me encanta lo que hacen 🔥

Noté que muchos clientes potenciales no los encuentran fácilmente en Google. En {company_name} tenemos una propuesta que les ayudaría muchísimo a conseguir más clientes.

¿Les cuento más? Solo toma 5 minutos 🚀"""

    TEMPLATE_SEGUIMIENTO: str = """Hola {contacto} 👋

Te escribo de nuevo de {company_name}. 

¿Tuviste oportunidad de revisar nuestra propuesta para {nombre_negocio}?

Muchos negocios como el tuyo han duplicado sus clientes en línea. Me gustaría contarte cómo.

¿Tienes 10 minutos esta semana? 📅

Saludos,
{agent_name}"""
