"""
Scheduler de seguimientos automáticos — SKY Eleven Bot
========================================================
Corre en paralelo al bot y maneja:
- Seguimiento día 3 (sin respuesta)
- Seguimiento día 7 (último intento)
- Recordatorio el día anterior a la reunión

ARRANCAR EN PARALELO:
    python scheduler.py
"""

import asyncio
import logging
import schedule
import time
import httpx
import random
from datetime import datetime
from conversation import ConversationManager, Estado
from templates import ESTADOS
from config import Config

log = logging.getLogger("Scheduler")
config = Config()
conv_manager = ConversationManager(config.DB_PATH)


async def enviar_mensaje(telefono: str, texto: str):
    """Envía mensaje vía Evolution API"""
    url = f"{config.EVOLUTION_API_URL}/message/sendText/{config.EVOLUTION_INSTANCE}"
    payload = {"number": telefono, "text": texto, "delay": 2000}
    headers = {"Content-Type": "application/json", "apikey": config.EVOLUTION_API_KEY}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()


async def seguimientos_automaticos():
    """Envía seguimientos a quien no respondió en 3 días"""
    log.info("📬 Revisando seguimientos pendientes...")

    sin_respuesta_3d = conv_manager.obtener_sin_respuesta(dias=3)
    sin_respuesta_7d = conv_manager.obtener_sin_respuesta(dias=7)

    # Seguimiento día 3
    for conv in sin_respuesta_3d:
        if conv["seguimientos"] == 0:
            msg = random.choice(ESTADOS["SEGUIMIENTO_3D"]).format(
                contacto=conv.get("nombre", ""),
                negocio=conv.get("negocio", "")
            )
            await enviar_mensaje(conv["telefono"], msg)
            conv_manager.incrementar_seguimiento(conv["telefono"])
            log.info(f"   📨 Seguimiento día 3 enviado a {conv.get('nombre')}")
            await asyncio.sleep(10)  # Espaciar envíos

    # Seguimiento día 7 (último)
    for conv in sin_respuesta_7d:
        if conv["seguimientos"] == 1:
            msg = random.choice(ESTADOS["SEGUIMIENTO_7D"]).format(
                contacto=conv.get("nombre", ""),
                negocio=conv.get("negocio", "")
            )
            await enviar_mensaje(conv["telefono"], msg)
            conv_manager.incrementar_seguimiento(conv["telefono"])

            # Marcar como muerto después del 2do seguimiento
            conv_manager._actualizar_estado(conv["telefono"], Estado.MUERTO)
            log.info(f"   💀 Último seguimiento enviado a {conv.get('nombre')} → MUERTO")
            await asyncio.sleep(10)


async def recordatorios_reunion():
    """Envía recordatorio el día anterior a la reunión"""
    log.info("🗓 Revisando recordatorios de reuniones...")

    pendientes = conv_manager.obtener_para_recordatorio()
    hoy = datetime.now().strftime("%A").lower()  # día actual en español sería mejor

    dias_mañana = {
        "monday": "martes", "tuesday": "miércoles", "wednesday": "jueves",
        "thursday": "viernes", "friday": "sábado", "saturday": "lunes", "sunday": "lunes"
    }
    manana = dias_mañana.get(hoy, "")

    for conv in pendientes:
        dia_reunion = (conv.get("dia_reunion") or "").lower()
        # Si la reunión es mañana → mandar recordatorio
        if manana and manana in dia_reunion:
            msg = random.choice(ESTADOS["RECORDATORIO_REUNION"]).format(
                contacto=conv.get("nombre", ""),
                hora=conv.get("hora_reunion", "el horario acordado")
            )
            await enviar_mensaje(conv["telefono"], msg)
            log.info(f"   🔔 Recordatorio enviado a {conv.get('nombre')}")
            await asyncio.sleep(5)


async def resumen_diario():
    """Manda a Gerardo un resumen del día"""
    cur = conv_manager.db.execute("""
        SELECT estado, COUNT(*) FROM sky_conversaciones GROUP BY estado
    """)
    estados = {r[0]: r[1] for r in cur.fetchall()}

    resumen = f"""📊 *Resumen del día — SKY Eleven Bot*

🗓 Reuniones agendadas hoy: {estados.get('agendado', 0)}
💬 Conversaciones activas: {sum(v for k,v in estados.items() if k not in ['agendado','no_interesado','muerto'])}
❌ No interesados: {estados.get('no_interesado', 0)}
💀 Sin respuesta: {estados.get('muerto', 0)}

_Bot funcionando correctamente_ ✅"""

    await enviar_mensaje(config.WSP_NUMERO_DESTINO, resumen)
    log.info("📊 Resumen diario enviado a Gerardo")


def run_async(coro):
    asyncio.run(coro)


def iniciar_scheduler():
    log.info("⏰ Scheduler de seguimientos iniciado")

    # Seguimientos: revisar todos los días a las 10am y 4pm
    schedule.every().day.at("10:00").do(lambda: run_async(seguimientos_automaticos()))
    schedule.every().day.at("16:00").do(lambda: run_async(seguimientos_automaticos()))

    # Recordatorios de reunión: revisar a las 9am todos los días
    schedule.every().day.at("09:00").do(lambda: run_async(recordatorios_reunion()))

    # Resumen diario a las 8pm
    schedule.every().day.at("20:00").do(lambda: run_async(resumen_diario()))

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    iniciar_scheduler()
