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

# Logger con fallback por si logger_utils no existe en Railway
try:
    from logger_utils import setup_logging
    log = setup_logging("bot.log")
    log = logging.getLogger("Server")
except Exception:
    logging.basicConfig(level=logging.INFO)
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
except Exception as e:
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
    """Sirve el dashboard maestro"""
    html_path = Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>dashboard.html no encontrado</h1>")

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Sirve la página de inicio de sesión"""
    html_path = Path(__file__).parent / "login.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>login.html no encontrado</h1>")

@app.get("/auth/config")
async def get_auth_config():
    """Devuelve las claves públicas de Supabase para inicializar JS SDK"""
    return {
        "url": os.getenv("SUPABASE_URL", ""),
        "key": os.getenv("SUPABASE_KEY", "")
    }

# ─── MERCADOPAGO SUSCRIPCIONES ────────────────────────────────────────────────
@app.post("/pagos/crear-suscripcion")
async def crear_suscripcion(request: Request):
    """Crea un link de pago de suscripción mensual con MercadoPago"""
    try:
        data = await request.json()
        empresa_id = data.get("empresa_id", "")
        plan = data.get("plan", "pro")
        PRECIOS = {"starter": 9700, "pro": 19700, "enterprise": 49700}  # en centavos ARS
        precio = PRECIOS.get(plan, 19700)
        mp_token = os.getenv("MP_ACCESS_TOKEN", "")
        if not mp_token:
            return JSONResponse({"ok": False, "error": "Falta MP_ACCESS_TOKEN en variables de entorno"}, status_code=400)
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.mercadopago.com/checkout/preferences",
                headers={"Authorization": f"Bearer {mp_token}", "Content-Type": "application/json"},
                json={
                    "items": [{"title": f"SKY Eleven SaaS - Plan {plan.upper()}", "quantity": 1, "unit_price": precio / 100, "currency_id": "ARS"}],
                    "external_reference": empresa_id,
                    "back_urls": {"success": os.getenv("APP_URL", "http://127.0.0.1:3000") + "/pagos/success", "failure": os.getenv("APP_URL", "http://127.0.0.1:3000") + "/pagos/failure"},
                    "auto_return": "approved",
                    "notification_url": os.getenv("APP_URL", "http://127.0.0.1:3000") + "/pagos/webhook"
                }
            )
            resp.raise_for_status()
            pref = resp.json()
            return {"ok": True, "init_point": pref.get("init_point"), "preference_id": pref.get("id")}
    except Exception as e:
        log.error(f"Error MP crear suscripción: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/pagos/webhook")
async def mp_webhook(request: Request):
    """Recibe confirmaciones de pago de MercadoPago y activa la cuenta del cliente"""
    try:
        data = await request.json()
        if data.get("type") == "payment":
            payment_id = data.get("data", {}).get("id")
            log.info(f"✅ Pago MP recibido: {payment_id}")
            # Aquí activaríamos is_active=True para el empresa_id del external_reference
        return {"ok": True}
    except Exception as e:
        log.error(f"Error MP webhook: {e}")
        return {"ok": False}

@app.get("/pagos/success")
async def pago_exitoso():
    return HTMLResponse("<html><body style='background:#080b10;color:#00e5a0;font-family:Inter;text-align:center;padding:80px'><h1>✅ Pago exitoso</h1><p>Tu suscripción fue activada. <a href='/' style='color:#00d4ff'>Volver al Dashboard</a></p></body></html>")

@app.get("/pagos/failure")  
async def pago_fallido():
    return HTMLResponse("<html><body style='background:#080b10;color:#ff5555;font-family:Inter;text-align:center;padding:80px'><h1>❌ Pago no completado</h1><p><a href='/' style='color:#00d4ff'>Volver al Dashboard</a></p></body></html>")

# ─── AUDIO IA ─────────────────────────────────────────────────────────────────
@app.post("/audio/generar")
async def generar_audio(request: Request):
    """Genera un audio de voz IA para enviar a un prospecto usando OpenAI TTS"""
    try:
        data = await request.json()
        texto = data.get("texto", "")
        prospecto_nombre = data.get("nombre", "amigo")
        api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "")
        
        if not texto:
            texto = f"Hola {prospecto_nombre}! Te llamo de parte de {cfg_server.COMPANY_NAME}. Vi que tu negocio tiene una oportunidad increíble que me gustaría comentarte. ¿Podemos hablar 5 minutos?"
        
        # Intentar con OpenAI TTS si hay API key
        if os.getenv("OPENAI_API_KEY"):
            import httpx, base64
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}", "Content-Type": "application/json"},
                    json={"model": "tts-1", "voice": "nova", "input": texto, "response_format": "mp3"}
                )
                resp.raise_for_status()
                audio_b64 = base64.b64encode(resp.content).decode()
                return {"ok": True, "audio_base64": audio_b64, "formato": "mp3", "texto": texto}
        else:
            # Sin API key: devolvemos el texto para que el usuario pueda grabarlo manualmente
            return {"ok": False, "sin_api_key": True, "texto_sugerido": texto, "mensaje": "Configura OPENAI_API_KEY en tus variables de entorno para generar audios automáticos"}
    except Exception as e:
        log.error(f"Error generando audio: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# ─── WHATSAPP QR DINÁMICO ─────────────────────────────────────────────────────
@app.post("/whatsapp/crear-instancia")
async def crear_instancia_wa(request: Request):
    """Crea una nueva instancia de WhatsApp en Evolution API para un empresa_id"""
    try:
        data = await request.json()
        empresa_id = data.get("empresa_id", "")
        if not empresa_id:
            return JSONResponse({"ok": False, "error": "empresa_id requerido"}, status_code=400)
        evolution_url = os.getenv("EVOLUTION_API_URL", "http://127.0.0.1:8080")
        evolution_key = os.getenv("EVOLUTION_API_KEY", "")
        instancia_nombre = f"sky_{empresa_id[:8]}"
        import httpx
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{evolution_url}/instance/create",
                headers={"apikey": evolution_key, "Content-Type": "application/json"},
                json={"instanceName": instancia_nombre, "qrcode": True, "integration": "WHATSAPP-BAILEYS"}
            )
            resp.raise_for_status()
            result = resp.json()
            return {"ok": True, "instancia": instancia_nombre, "qr_code": result.get("qrcode", {}).get("base64", ""), "data": result}
    except Exception as e:
        log.error(f"Error creando instancia WA: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/whatsapp/qr/{empresa_id}")
async def obtener_qr(empresa_id: str):
    """Devuelve el código QR actual para conectar WhatsApp de un inquilino"""
    try:
        evolution_url = os.getenv("EVOLUTION_API_URL", "http://127.0.0.1:8080")
        evolution_key = os.getenv("EVOLUTION_API_KEY", "")
        instancia_nombre = f"sky_{empresa_id[:8]}"
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{evolution_url}/instance/connect/{instancia_nombre}",
                headers={"apikey": evolution_key}
            )
            resp.raise_for_status()
            result = resp.json()
            return {"ok": True, "qr_base64": result.get("base64", ""), "connected": result.get("instance", {}).get("state") == "open"}
    except Exception as e:
        log.error(f"Error obteniendo QR: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

# ─── API ENDPOINTS ────────────────────────────────────────────────────────────

@app.get("/prospectos")
async def get_prospectos(request: Request):
    """Retorna todos los prospectos del CRM del inquilino"""
    if not BOT_DISPONIBLE:
        return []
    try:
        tenant_id = request.headers.get("x-user-id")
        if not tenant_id and not getattr(cfg_server, "IS_MASTER", False):
            return []

        is_pg = getattr(conv_manager.db, 'is_pg', False)
        where_clause = ""
        params = []

        if not getattr(cfg_server, "IS_MASTER", False):
            where_clause = "WHERE p.empresa_id = %s" if is_pg else "WHERE p.empresa_id = ?"
            params.append(tenant_id)

        cur = conv_manager.db.execute(f"""
            SELECT p.*, c.estado as conv_estado, c.bot_activo
            FROM sky_prospectos p
            LEFT JOIN sky_conversaciones c ON c.prospecto_id = p.id
            {where_clause}
            ORDER BY p.fecha_creacion DESC
            LIMIT 200
        """, tuple(params))
        
        rows = [dict(r) for r in cur.fetchall()]
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
    
    tenant_id = request.headers.get("x-user-id")
    if not tenant_id and not getattr(cfg_server, "IS_MASTER", False):
        return JSONResponse({"ok": False, "error": "No autorizado"}, status_code=401)
        
    empresa_val = tenant_id if tenant_id else getattr(cfg_server, "EMPRESA_ID", None)
    
    # Generar hash para deduplicar
    import hashlib
    tel_clean = (telefono or "").strip().replace(" ", "")
    biz_clean = (nombre_negocio or "").lower().strip()
    hash_val = hashlib.md5(f"{tel_clean}_{biz_clean}".encode()).hexdigest()
    
    try:
        from datetime import datetime
        is_pg = getattr(conv_manager.db, 'is_pg', False)
        ph = '%s' if is_pg else '?'
        
        conv_manager.db.execute(f"""
            INSERT INTO sky_prospectos (
                nombre_negocio, contacto, telefono, email, ciudad, 
                categoria, fuente, stage, fecha_creacion, hash_unico, empresa_id
            ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """, (
            nombre_negocio, contacto, telefono, email, ciudad, 
            categoria, fuente, "Nuevo", datetime.now().isoformat(), hash_val, empresa_val
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
async def get_conversaciones(request: Request):
    """Retorna conversaciones activas con mensajes"""
    if not BOT_DISPONIBLE:
        return []

    tenant_id = request.headers.get("x-user-id")
    if not tenant_id and not getattr(cfg_server, "IS_MASTER", False):
        return []

    is_pg = getattr(conv_manager.db, 'is_pg', False)
    ph = '%s' if is_pg else '?'
    
    where_clause = "WHERE estado NOT IN ('muerto')"
    params = []
    
    if not getattr(cfg_server, "IS_MASTER", False):
        where_clause += f" AND empresa_id = {ph}"
        params.append(tenant_id)

    cur = conv_manager.db.execute(f"""
        SELECT * FROM sky_conversaciones
        {where_clause}
        ORDER BY fecha_update DESC
        LIMIT 50
    """, tuple(params))
    
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
async def get_stats(request: Request):
    """Stats del sistema"""
    if not BOT_DISPONIBLE:
        return {"total": 0, "hot": 0, "por_etapa": {}, "conversaciones": {}}

    tenant_id = request.headers.get("x-user-id")
    if not tenant_id and not getattr(cfg_server, "IS_MASTER", False):
        return {"total": 0, "hot": 0, "por_etapa": {}, "conversaciones": {}}

    is_pg = getattr(conv_manager.db, 'is_pg', False)
    ph = '%s' if is_pg else '?'
    
    where_p = ""
    where_c = ""
    params = []
    
    if not getattr(cfg_server, "IS_MASTER", False):
        where_p = f"WHERE empresa_id = {ph}"
        where_c = f"WHERE empresa_id = {ph}"
        params.append(tenant_id)

    cur = conv_manager.db.execute(f"SELECT stage, COUNT(*) FROM sky_prospectos {where_p} GROUP BY stage", tuple(params))
    por_etapa = {r[0]: r[1] for r in cur.fetchall()}

    cur2 = conv_manager.db.execute(f"SELECT COUNT(*) FROM sky_prospectos {where_p}", tuple(params))
    total = cur2.fetchone()[0]

    where_hot = f"WHERE score >= 70 AND empresa_id = {ph}" if not getattr(cfg_server, "IS_MASTER", False) else "WHERE score >= 70"
    params_hot = [tenant_id] if not getattr(cfg_server, "IS_MASTER", False) else []
    
    cur3 = conv_manager.db.execute(f"SELECT COUNT(*) FROM sky_prospectos {where_hot}", tuple(params_hot))
    hot = cur3.fetchone()[0]

    cur4 = conv_manager.db.execute(f"SELECT estado, COUNT(*) FROM sky_conversaciones {where_c} GROUP BY estado", tuple(params))
    conv_estados = {r[0]: r[1] for r in cur4.fetchall()}

    return {
        "total": total,
        "hot": hot,
        "por_etapa": por_etapa,
        "conversaciones": conv_estados,
    }

# ─── ADMIN Y AUTH ─────────────────────────────────────────────────────────────
@app.get("/auth/me")
async def get_me():
    """Confirma al frontend si la sesión de la API tiene privilegios maestros o no"""
    return {"is_master": getattr(cfg_server, "IS_MASTER", False)}

@app.get("/admin/clientes")
async def get_clientes(request: Request):
    """(Admin View) Estadísticas agregadas de todos los inquilinos (agencias)"""
    if not getattr(cfg_server, "IS_MASTER", False):
        return JSONResponse({"error": "No autorizado (Se requiere IS_MASTER)"}, status_code=403)
    try:
        cur = conv_manager.db.execute("""
            SELECT empresa_id, COUNT(*) as total_leads, MAX(fecha_creacion) as last_activity
            FROM sky_prospectos
            GROUP BY empresa_id
        """)
        results = [dict(row) for row in cur.fetchall()]
        # Completar con nombres nulos por defecto, si luego cruzamos UUID con correos de otra forma
        for r in results:
            if not r['empresa_id']: r['empresa_id'] = "Agencia Desconocida"
        return results
    except Exception as e:
        log.error(f"Error GET /admin/clientes: {e}")
        return []

@app.get("/admin/cliente/{empresa_id}/leads")
async def get_cliente_leads(empresa_id: str):
    """(Admin) Ver los últimos 20 prospectos de un cliente específico"""
    if not getattr(cfg_server, "IS_MASTER", False):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    try:
        ph = "%s" if conv_manager.db.db_type == "postgres" else "?"
        cur = conv_manager.db.execute(
            f"SELECT nombre_negocio, telefono, score, stage, fuente, fecha_creacion FROM sky_prospectos WHERE empresa_id = {ph} ORDER BY fecha_creacion DESC LIMIT 20",
            (empresa_id,)
        )
        return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        log.error(f"Error GET /admin/cliente leads: {e}")
        return []

@app.post("/admin/cliente/{empresa_id}/toggle")
async def toggle_cliente(empresa_id: str, request: Request):
    """(Admin) Activar o desactivar la cuenta de un inquilino"""
    if not getattr(cfg_server, "IS_MASTER", False):
        return JSONResponse({"error": "No autorizado"}, status_code=403)
    try:
        data = await request.json()
        activo = data.get("activo", True)
        ph = "%s" if conv_manager.db.db_type == "postgres" else "?"
        # Aseguramos que la tabla tiene la columna is_active
        try:
            conv_manager.db.execute(f"ALTER TABLE sky_prospectos ADD COLUMN IF NOT EXISTS cuenta_activa BOOLEAN DEFAULT TRUE")
        except:
            pass
        conv_manager.db.execute(
            f"UPDATE sky_prospectos SET cuenta_activa = {ph} WHERE empresa_id = {ph}",
            (activo, empresa_id)
        )
        return {"ok": True, "empresa_id": empresa_id, "activo": activo}
    except Exception as e:
        log.error(f"Error POST /admin/cliente toggle: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

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

# ─── ARRANQUE ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
