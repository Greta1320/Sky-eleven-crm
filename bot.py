"""
SKY Eleven WhatsApp Bot — Webhook Principal
============================================
Recibe mensajes de Evolution API y responde automáticamente.

Cómo funciona:
1. Evolution API recibe mensaje del prospecto
2. Evolution manda webhook POST a este servidor
3. Este bot procesa el mensaje y responde vía Evolution API
4. Si se agenda reunión → avisa a Gerardo por WhatsApp

ARRANCAR:
    uvicorn bot:app --host 0.0.0.0 --port 3000 --reload

CONFIGURAR EN EVOLUTION API:
    Webhook URL: http://TU_IP:3000/webhook
    Eventos: messages.upsert
"""

import logging
import httpx
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from conversation import ConversationManager, Estado
from templates import ESTADOS
from config import Config

from logger_utils import setup_logging
log = setup_logging("bot.log")
log = logging.getLogger("Bot")

app    = FastAPI(title="SKY Eleven Bot")
config = Config()
conv_manager = ConversationManager(config.DB_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK — Evolution API manda todos los mensajes acá
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """Recibe el webhook de Evolution API"""
    try:
        data = await request.json()
        log.info(f"Webhook recibido: {str(data)[:200]}")

        # Evolution API manda distintos eventos, nos interesa messages.upsert
        evento = data.get("event", "")
        if evento != "messages.upsert":
            return JSONResponse({"status": "ignorado", "evento": evento})

        mensaje_data = data.get("data", {})

        # Ignorar mensajes propios (los que manda el bot)
        if mensaje_data.get("key", {}).get("fromMe"):
            return JSONResponse({"status": "propio"})

        # Extraer datos del mensaje
        telefono = mensaje_data.get("key", {}).get("remoteJid", "").replace("@s.whatsapp.net", "")
        
        # Extraer texto (puede venir en distintas estructuras)
        texto = (
            mensaje_data.get("message", {}).get("conversation") or
            mensaje_data.get("message", {}).get("extendedTextMessage", {}).get("text") or
            mensaje_data.get("message", {}).get("imageMessage", {}).get("caption") or
            ""
        )

        if not telefono or not texto:
            return JSONResponse({"status": "sin_datos"})

        log.info(f"📨 Mensaje de {telefono}: {texto[:80]}")

        # Procesar en background para responder rápido al webhook
        background_tasks.add_task(procesar_y_responder, telefono, texto)

        return JSONResponse({"status": "ok"})

    except Exception as e:
        log.error(f"Error en webhook: {e}")
        return JSONResponse({"status": "error", "msg": str(e)}, status_code=500)


# ─────────────────────────────────────────────────────────────────────────────
# LÓGICA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

async def procesar_y_responder(telefono: str, mensaje: str):
    """Procesa el mensaje y envía la respuesta correspondiente"""
    try:
        # Esperar 1-3 segundos para parecer humano (no responder instantáneo)
        await asyncio.sleep(2)

        # Obtener respuesta del bot
        respuesta = conv_manager.procesar(telefono, mensaje)

        if respuesta:
            await enviar_mensaje(telefono, respuesta)

            # Verificar si acaba de quedar agendado → avisar a Gerardo
            conv = conv_manager._obtener_conversacion(telefono)
            if conv and conv["estado"] == Estado.AGENDADO:
                await notificar_reunion_gerardo(conv)

    except Exception as e:
        log.error(f"Error procesando mensaje de {telefono}: {e}")


async def enviar_mensaje(telefono: str, texto: str):
    """Envía mensaje vía Evolution API"""
    url = f"{config.EVOLUTION_API_URL}/message/sendText/{config.EVOLUTION_INSTANCE}"
    payload = {
        "number": telefono,
        "text":   texto,
        "delay":  1500   # 1.5 segundos de delay — más natural
    }
    headers = {
        "Content-Type": "application/json",
        "apikey": config.EVOLUTION_API_KEY
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        log.info(f"✅ Respuesta enviada a {telefono}: {texto[:60]}...")


async def notificar_reunion_gerardo(conv: dict):
    """Avisa a Gerardo por WhatsApp que se agendó una reunión"""
    await asyncio.sleep(3)  # Pequeño delay antes de notificar

    mensaje = ESTADOS["ALERTA_GERARDO"].format(
        contacto  = conv.get("nombre", "—"),
        negocio   = conv.get("negocio", "—"),
        dia       = conv.get("dia_reunion", "—"),
        hora      = conv.get("hora_reunion", "—"),
        telefono  = conv.get("telefono", "—"),
        fuente    = "WhatsApp Bot",
        score     = "—",
        resumen   = conv.get("resumen", "Sin resumen aún"),
        crm_link  = f"http://localhost:5000/crm/{conv.get('prospecto_id', '')}",
    )

    await enviar_mensaje(config.WSP_NUMERO_DESTINO, mensaje)
    log.info(f"🗓 Gerardo notificado: reunión con {conv.get('nombre')} el {conv.get('dia_reunion')}")


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS EXTRAS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/iniciar")
async def iniciar_conversacion(request: Request):
    """
    Gerardo llama a este endpoint DESPUÉS de mandar el primer mensaje manual.
    Registra la conversación para que el bot empiece a responder.

    Body: { "telefono": "541112345678", "nombre": "Carlos", "negocio": "Restaurante El Sol", "prospecto_id": 42 }
    """
    data = await request.json()
    telefono     = data.get("telefono", "")
    nombre       = data.get("nombre", "")
    negocio      = data.get("negocio", "")
    prospecto_id = data.get("prospecto_id")

    if not telefono:
        return JSONResponse({"error": "telefono requerido"}, status_code=400)

    conv_manager.inicializar_conversacion(telefono, nombre, negocio, prospecto_id)
    log.info(f"✅ Conversación iniciada: {nombre} / {negocio} / {telefono}")

    return JSONResponse({
        "status": "ok",
        "mensaje": f"Bot activado para {nombre}. Cuando responda, el bot toma el hilo automáticamente."
    })


@app.get("/conversaciones")
async def listar_conversaciones():
    """Ver todas las conversaciones activas"""
    cur = conv_manager.db.execute("""
        SELECT telefono, nombre, negocio, estado, dia_reunion, hora_reunion,
               seguimientos, fecha_update
        FROM sky_conversaciones
        ORDER BY fecha_update DESC
        LIMIT 50
    """)
    return [dict(r) for r in cur.fetchall()]


@app.get("/stats")
async def stats():
    """Stats rápidas del bot"""
    cur = conv_manager.db.execute("""
        SELECT estado, COUNT(*) as cantidad
        FROM sky_conversaciones
        GROUP BY estado
    """)
    estados = {r[0]: r[1] for r in cur.fetchall()}

    cur2 = conv_manager.db.execute("SELECT COUNT(*) FROM sky_mensajes")
    total_msgs = cur2.fetchone()[0]

    return {
        "conversaciones": estados,
        "total_mensajes": total_msgs,
        "agendadas": estados.get("agendado", 0),
        "activas": sum(v for k, v in estados.items() if k not in ["agendado", "no_interesado", "muerto"])
    }


@app.get("/health")
async def health():
    return {"status": "ok", "bot": "SKY Eleven activo 🚀"}
