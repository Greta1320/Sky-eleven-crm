"""
SKY Eleven — Servidor Dashboard + API
=======================================
Sirve el dashboard en http://localhost:3000
y expone los endpoints que el frontend necesita.

ARRANCAR:
    uvicorn server:app --host 0.0.0.0 --port 3000 --reload
"""

import logging
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env antes de cualquier otro import del proyecto
load_dotenv()

from logger_utils import setup_logging
log = setup_logging("bot.log")
log = logging.getLogger("Server")

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Importar el bot y el conversation manager
try:
    from bot import app as bot_app, conv_manager, procesar_y_responder, notificar_reunion_gerardo
    from conversation import ConversationManager, Estado
    from config import Config
    BOT_DISPONIBLE = True
except ImportError as e:
    log.warning(f"Bot no disponible: {e}")
    BOT_DISPONIBLE = False

app = FastAPI(title="SKY Eleven Dashboard")

# CORS para que el frontend pueda hacer fetch
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── DASHBOARD HTML ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Sirve el dashboard"""
    html_path = Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>dashboard.html no encontrado</h1>")

# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/prospectos")
async def get_prospectos():
    """Retorna todos los prospectos del CRM"""
    if not BOT_DISPONIBLE:
        return []
    cur = conv_manager.db.execute("""
        SELECT p.*, c.estado as conv_estado, c.bot_activo
        FROM sky_prospectos p
        LEFT JOIN sky_conversaciones c ON c.prospecto_id = p.id
        ORDER BY p.fecha_creacion DESC
        LIMIT 200
    """)
    rows = [dict(r) for r in cur.fetchall()]
    # Normalizar campos para el frontend
    for r in rows:
        r["bot_activo"] = bool(r.get("bot_activo"))
        r["stage"] = r.get("stage", "Nuevo")
    return rows

@app.patch("/prospectos/{id}/stage")
async def update_stage(id: int, request: Request):
    """Cambia la etapa de un prospecto"""
    data = await request.json()
    stage = data.get("stage")
    if not stage or not BOT_DISPONIBLE:
        return JSONResponse({"ok": False})
    conv_manager.db.execute(
        "UPDATE sky_prospectos SET stage = ? WHERE id = ?", (stage, id)
    )
    conv_manager.db.commit()
    return {"ok": True}

@app.patch("/prospectos/{id}/nota")
async def add_nota(id: int, request: Request):
    """Agrega una nota a un prospecto"""
    data = await request.json()
    nota = data.get("nota", "")
    if not nota or not BOT_DISPONIBLE:
        return JSONResponse({"ok": False})
    cur = conv_manager.db.execute("SELECT notas FROM sky_prospectos WHERE id = ?", (id,))
    row = cur.fetchone()
    notas_actuales = row[0] if row and row[0] else ""
    from datetime import datetime
    nueva_nota = notas_actuales + f"\n📝 {nota} [{datetime.now().strftime('%d/%m %H:%M')}]"
    conv_manager.db.execute("UPDATE sky_prospectos SET notas = ? WHERE id = ?", (nueva_nota, id))
    conv_manager.db.commit()
    return {"ok": True}

@app.get("/conversaciones")
async def get_conversaciones():
    """Retorna conversaciones activas con mensajes"""
    if not BOT_DISPONIBLE:
        return []
    cur = conv_manager.db.execute("""
        SELECT * FROM sky_conversaciones
        WHERE estado NOT IN ('muerto')
        ORDER BY fecha_update DESC
        LIMIT 50
    """)
    convs = [dict(r) for r in cur.fetchall()]

    # Agregar mensajes de cada conversación
    for conv in convs:
        cur2 = conv_manager.db.execute("""
            SELECT direccion as dir, mensaje as texto,
                   substr(fecha, 12, 5) as hora
            FROM sky_mensajes
            WHERE telefono = ?
            ORDER BY fecha ASC
            LIMIT 50
        """, (conv["telefono"],))
        conv["mensajes"] = [dict(r) for r in cur2.fetchall()]

    return convs

@app.post("/iniciar")
async def iniciar_conv(request: Request):
    """Activa el bot para un número específico"""
    data = await request.json()
    telefono     = data.get("telefono", "")
    nombre       = data.get("nombre", "")
    negocio      = data.get("negocio", "")
    prospecto_id = data.get("prospecto_id")

    if not telefono:
        return JSONResponse({"error": "telefono requerido"}, status_code=400)

    if BOT_DISPONIBLE:
        conv_manager.inicializar_conversacion(telefono, nombre, negocio, prospecto_id)

        # Marcar lead como bot_activo en prospectos
        if prospecto_id:
            conv_manager.db.execute(
                "UPDATE sky_prospectos SET stage = 'Contactado' WHERE id = ?",
                (prospecto_id,)
            )
            conv_manager.db.commit()

    log.info(f"✅ Bot activado para {nombre} / {negocio} / {telefono}")
    return {"ok": True, "mensaje": f"Bot activado para {nombre}"}

@app.post("/agent/start")
async def agent_start():
    """Activa el agente (scheduler)"""
    return {"ok": True, "status": "running"}

@app.post("/agent/run")
async def agent_run(background_tasks: BackgroundTasks):
    """Fuerza un ciclo de scraping inmediatamente en background"""
    try:
        from agent import SkyElevenAgent
        agente = SkyElevenAgent()
        background_tasks.add_task(agente.run_cycle)
        return {"ok": True, "status": "started", "mensaje": "Buscando en segundo plano..."}
    except Exception as e:
        log.error(f"Error iniciando bot: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/agent/stop")
async def agent_stop():
    """Pausa el agente"""
    return {"ok": True, "status": "stopped"}

@app.post("/config")
async def save_config(request: Request):
    """Guarda la configuración de búsqueda"""
    import json
    try:
        data = await request.json()
        with open("sky_config.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return {"ok": True}
    except Exception as e:
        log.error(f"Error guardando configuracion: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/logs")
async def get_logs():
    """Devuelve las últimas líneas del log para el dashboard"""
    try:
        if not os.path.exists("bot.log"):
            return {"logs": []}
            
        with open("bot.log", "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            
        parsed_logs = []
        import re as _re
        # Regex para líneas de log reales: YYYY-MM-DD HH:MM:SS,ms [LEVEL] Mensaje
        log_pattern = _re.compile(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}):\d{2},\d+ \[(\w+)\] (.+)')
        
        for line in reversed(lines):
            line = line.strip()
            if not line: continue
            
            m = log_pattern.match(line)
            if not m:
                continue  # Ignorar traceback / líneas de continuación
            
            time_str = m.group(2)   # HH:MM
            level    = m.group(3)   # INFO / ERROR
            msg      = m.group(4).strip()
            
            # Elegir el ícono según contenido
            if "Error" in msg or level == "ERROR":
                txt = "❌ " + msg
            elif "Escaneando" in msg or "Google Maps" in msg or "🗺" in msg:
                txt = "🔍 " + msg
            elif "WhatsApp" in msg or "WA" in msg or "📱" in msg:
                txt = "📱 " + msg
            elif "calificad" in msg.lower() or "prospecto" in msg.lower():
                txt = "⭐ " + msg
            elif "iniciado" in msg.lower() or "ciclo" in msg.lower():
                txt = "🚀 " + msg
            else:
                txt = msg

            parsed_logs.append({"t": time_str, "txt": txt, "found": None})
            
            if len(parsed_logs) >= 40:
                break
            
        return {"logs": parsed_logs}
    except Exception as e:
        return {"logs": [{"t": "err", "txt": f"Error leyendo logs: {e}", "found": None}]}


@app.get("/stats")
async def get_stats():
    """Stats del sistema"""
    if not BOT_DISPONIBLE:
        return {"total": 0, "hot": 0, "por_etapa": {}, "conversaciones": {}}

    cur = conv_manager.db.execute(
        "SELECT stage, COUNT(*) FROM sky_prospectos GROUP BY stage"
    )
    por_etapa = {r[0]: r[1] for r in cur.fetchall()}

    cur2 = conv_manager.db.execute("SELECT COUNT(*) FROM sky_prospectos")
    total = cur2.fetchone()[0]

    cur3 = conv_manager.db.execute(
        "SELECT COUNT(*) FROM sky_prospectos WHERE score >= 70"
    )
    hot = cur3.fetchone()[0]

    cur4 = conv_manager.db.execute(
        "SELECT estado, COUNT(*) FROM sky_conversaciones GROUP BY estado"
    )
    conv_estados = {r[0]: r[1] for r in cur4.fetchall()}

    return {
        "total": total,
        "hot": hot,
        "por_etapa": por_etapa,
        "conversaciones": conv_estados,
    }

@app.get("/health")
async def health():
    return {"status": "ok", "dashboard": "SKY Eleven 🚀", "bot": BOT_DISPONIBLE}

# ─── WEBHOOK (del bot, mismo servidor) ───────────────────────────────────────
if BOT_DISPONIBLE:
    from bot import webhook, iniciar_conversacion
    app.add_api_route("/webhook", webhook, methods=["POST"])
