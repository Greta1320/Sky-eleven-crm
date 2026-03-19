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
    from config import Config
    cfg_server = Config()
    from bot import app as bot_app, conv_manager, procesar_y_responder, notificar_reunion_gerardo
    from conversation import ConversationManager, Estado
    # Asegurar que el conv_manager del servidor sea el mismo o use la misma DB
    conv_manager.db.close() # Cerrar el default si existe
    conv_manager = ConversationManager(cfg_server.DB_PATH) # Forzar la DB correcta
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
    try:
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
    except Exception as e:
        log.error(f"Error fetching prospectos: {e}")
        return []

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

@app.post("/prospectos/manual")
async def add_prospecto_manual(request: Request):
    """Agrega un prospecto cargado manualmente desde el dashboard"""
    data = await request.json()
    nombre_negocio = data.get("nombre_negocio")
    contacto       = data.get("contacto")
    telefono       = data.get("telefono")
    email          = data.get("email")
    ciudad         = data.get("ciudad", "")
    categoria      = data.get("categoria", "Manual")
    fuente         = "Manual"
    
    if not nombre_negocio:
        return JSONResponse({"ok": False, "error": "Nombre de negocio requerido"}, status_code=400)
    
    # Generar hash para deduplicar
    import hashlib
    tel_clean = (telefono or "").strip().replace(" ", "")
    biz_clean = (nombre_negocio or "").lower().strip()
    hash_val = hashlib.md5(f"{tel_clean}_{biz_clean}".encode()).hexdigest()
    
    try:
        from datetime import datetime
        conv_manager.db.execute("""
            INSERT INTO sky_prospectos (
                nombre_negocio, contacto, telefono, email, ciudad, 
                categoria, fuente, stage, fecha_creacion, hash_unico
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nombre_negocio, contacto, telefono, email, ciudad, 
            categoria, fuente, "Nuevo", datetime.now().isoformat(), hash_val
        ))
        conv_manager.db.commit()
        return {"ok": True, "mensaje": "Prospecto agregado con éxito"}
    except Exception as e:
        log.error(f"Error agregando prospecto manual: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/prospectos/{id}/analizar")
async def analizar_prospecto(id: int):
    """Analiza un prospecto con IA y genera un gancho de venta"""
    if not BOT_DISPONIBLE:
        return JSONResponse({"ok": False, "error": "Bot no disponible"}, status_code=500)
    
    try:
        from qualifier import ProspectQualifier
        from config import Config
        cfg = Config()
        qualifier = ProspectQualifier(cfg)
        
        cur = conv_manager.db.execute("SELECT * FROM sky_prospectos WHERE id = ?", (id,))
        row = cur.fetchone()
        if not row:
            return JSONResponse({"ok": False, "error": "Prospecto no encontrado"}, status_code=404)
        
        p = dict(row)
        
        # SI TIENE WEB PERO NO TELÉFONO/EMAIL, AUDITAMOS PARA ENCONTRARLOS
        found_data = {}
        if p.get("website") and (not p.get("telefono") or not p.get("email")):
            try:
                from ai_auditor import AIAuditor
                auditor = AIAuditor()
                audit_res = await auditor.auditar(p["website"])
                if audit_res:
                    if not p.get("telefono") and audit_res.get("telefono"):
                        found_data["telefono"] = audit_res["telefono"]
                        p["telefono"] = audit_res["telefono"]
                    if not p.get("email") and audit_res.get("email"):
                        found_data["email"] = audit_res["email"]
                        p["email"] = audit_res["email"]
                    if audit_res.get("gancho_venta"):
                        found_data["gancho"] = audit_res["gancho_venta"]
                        p["gancho"] = audit_res["gancho_venta"]
            except Exception as audit_err:
                print(f"Error en auditoría manual: {audit_err}")

        score, razon = qualifier.calificar(p)
        gancho = p.get("gancho") or ""
        
        if not gancho:
            # Generar gancho basado en reglas si no hay uno de auditoría
            nombre = p.get("nombre_negocio", "tu negocio")
            ciudad = p.get("ciudad", "tu zona")
            if not p.get("tiene_web"):
                gancho = f"Hola! Vi que {nombre} no tiene web propia. Estás perdiendo clientes en {ciudad} que hoy solo ven a tu competencia. ¿Te ayudo?"
            elif score > 80:
                gancho = f"¡Hola! Me impresionó tu negocio, {nombre}. Tienen un perfil premium y creo que con una web de alta conversión podrían duplicar sus agendamientos mensuales. ¿Charlamos?"
            else:
                gancho = f"Hola {nombre}, estuve analizando la competencia en {ciudad} y tengo una estrategia puntual para que ustedes se queden con los clientes que hoy se van a otros locales. ¿Les interesa?"

        # Actualizar en DB local (incluyendo posibles nuevos contactos)
        update_fields = ["score = ?", "razon_score = ?", "gancho = ?"]
        params = [score, razon, gancho]
        
        if "telefono" in found_data:
            update_fields.append("telefono = ?")
            params.append(found_data["telefono"])
        if "email" in found_data:
            update_fields.append("email = ?")
            params.append(found_data["email"])
        
        params.append(id)
        query = f"UPDATE sky_prospectos SET {', '.join(update_fields)} WHERE id = ?"
        
        conv_manager.db.execute(query, tuple(params))
        conv_manager.db.commit()
        
        return {
            "ok": True, 
            "score": score, 
            "razon": razon, 
            "gancho": gancho,
            "telefono": p.get("telefono"),
            "email": p.get("email")
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

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
    """Guarda la configuración de búsqueda y actualiza .env con credenciales"""
    import json
    import os
    try:
        data = await request.json()
        
        # 1. Guardar config general en JSON
        with open("sky_config.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        # 2. Actualizar .env si hay cuentas conectadas
        acc = data.get("accounts", {})
        if acc:
            env_path = ".env"
            env_content = ""
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    env_content = f.read()
            
            def update_env(key, val):
                nonlocal env_content
                import re
                if not val: return
                pattern = f"^{key}=.*"
                replacement = f"{key}={val}"
                if re.search(pattern, env_content, re.MULTILINE):
                    env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
                else:
                    env_content += f"\n{key}={val}"

            update_env("INSTAGRAM_USER", acc.get("ig_user"))
            update_env("INSTAGRAM_PASSWORD", acc.get("ig_pass"))
            update_env("LINKEDIN_USER", acc.get("li_user"))
            update_env("LINKEDIN_PASSWORD", acc.get("li_pass"))
            update_env("GOOGLE_MAPS_API_KEY", acc.get("gmaps_key"))
            
            # 3. Branding & Sync
            brand = data.get("branding", {})
            update_env("AGENT_NAME", brand.get("agent_name"))
            update_env("COMPANY_NAME", brand.get("company_name"))
            update_env("LICENSE_KEY", brand.get("license_key"))
            
            # 4. Persona & Autopilot
            ia_cfg = data.get("ia", {})
            update_env("ACTIVE_PERSONA", ia_cfg.get("active_persona", "general"))
            update_env("AUTOPILOT_MODE", str(ia_cfg.get("autopilot_mode", False)))
            update_env("WSP_AUTO_REPLY", str(ia_cfg.get("auto_reply", True)))
            
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(env_content.strip() + "\n")
            
            log.info("✅ .env actualizado con nuevas credenciales")

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

# ─── ROADMAP GENERATOR ────────────────────────────────────────────────────────
ROADMAPS_FILE = Path("sky_roadmaps.json")

def _cargar_roadmaps() -> list:
    if ROADMAPS_FILE.exists():
        return json.loads(ROADMAPS_FILE.read_text(encoding="utf-8"))
    return []

def _guardar_roadmaps(roadmaps: list):
    ROADMAPS_FILE.write_text(json.dumps(roadmaps, ensure_ascii=False, indent=2), encoding="utf-8")

@app.post("/roadmap/generar")
async def generar_roadmap_endpoint(request: Request):
    """Genera un roadmap de venta personalizado por cliente usando IA"""
    data = await request.json()
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JSONResponse({"ok": False, "error": "Falta ANTHROPIC_API_KEY en .env"}, status_code=400)
    try:
        from roadmap_generator import generar_roadmap
        resultado = await generar_roadmap(data, api_key)
        # Guardar en el archivo local
        roadmaps = _cargar_roadmaps()
        roadmaps.append(resultado)
        _guardar_roadmaps(roadmaps)
        return resultado
    except Exception as e:
        log.error(f"Error generando roadmap: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/roadmaps")
async def listar_roadmaps():
    """Lista todos los roadmaps guardados"""
    return _cargar_roadmaps()

@app.delete("/roadmap/{idx}")
async def eliminar_roadmap(idx: int):
    """Elimina un roadmap por índice"""
    roadmaps = _cargar_roadmaps()
    if 0 <= idx < len(roadmaps):
        roadmaps.pop(idx)
        _guardar_roadmaps(roadmaps)
        return {"ok": True}
    return JSONResponse({"ok": False, "error": "Índice no válido"}, status_code=404)

@app.get("/health")
async def health():
    return {"status": "ok", "dashboard": "SKY Eleven 🚀", "bot": BOT_DISPONIBLE}

# ─── WEBHOOK (del bot, mismo servidor) ───────────────────────────────────────
if BOT_DISPONIBLE:
    from bot import webhook, iniciar_conversacion
    app.add_api_route("/webhook", webhook, methods=["POST"])
