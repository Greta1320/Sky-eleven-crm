"""
Calificador IA de Prospectos — SKY Eleven
==========================================
Puntúa cada prospecto del 0-100 para priorizar el contacto.
Usa reglas de negocio + opcionalmente Claude AI para análisis profundo.
"""

import logging
import re
from typing import Tuple, Dict, Any
from config import Config

log = logging.getLogger("Qualifier")

# Categorías de ALTO valor para venta de web (más fácil cerrar)
CATEGORIAS_PREMIUM = [
    "restaurant", "restaurante", "clinica", "clínica", "dental", "medico", "médico",
    "abogado", "lawyer", "spa", "salon", "salón", "estetica", "estética",
    "constructora", "inmobiliaria", "hotel", "boutique", "academia",
    "consultorio", "arquitecto", "contador", "despacho",
]

# Palabras que indican web desactualizada en descripción
SEÑALES_SIN_WEB = [
    "whatsapp", "whatssap", "wa.me", "solo pedidos por",
    "mandanos mensaje", "escribenos", "sin web", "pronto web",
]

# Palabras que indican negocio activo y con dinero
SEÑALES_POSITIVAS = [
    "años de experiencia", "sucursales", "equipo", "staff",
    "reserva", "cita", "agenda", "premium", "lujoso",
]

# Palabras de urgencia para Lead Scoring Alto (FUEGO)
SEÑALES_URGENCIA = [
    "urgente", "colapsado", "pierdo plata", "perdiendo plata", "perdiendo ventas", 
    "no doy abasto", "no damos abasto", "necesito ayuda", "desesperado", "demora"
]


class ProspectQualifier:
    def __init__(self, config: Config):
        self.config = config
        self.claude = None
        if config.USAR_IA_CLAUDE and config.ANTHROPIC_API_KEY:
            self._init_claude()

    def _init_claude(self):
        try:
            import anthropic
            self.claude = anthropic.Anthropic(api_key=self.config.ANTHROPIC_API_KEY)
            log.info("✅ Claude AI conectado para calificación")
        except ImportError:
            log.warning("anthropic no instalado. Usando solo reglas de negocio.")

    def calificar(self, prospect: Dict[str, Any]) -> Tuple[int, str]:
        """
        Retorna (score: int, razon: str)
        Score 0-100, donde 70+ = prospecto HOT
        """
        score = 20  # Base score for any localized business
        razones = ["Negocio local detectado (+20)"]

        # ─── REGLAS DE NEGOCIO (siempre se aplican) ───────────────

        # 1. Sin web o web vacía → señal fuerte de necesidad
        if not prospect.get("tiene_web") or not prospect.get("website"):
            score += 30
            razones.append("Sin sitio web detectado (+30)")
        else:
            # Senior Rule: Usar datos de auditoría si existen
            audit = prospect.get("audit_data", {})
            if audit:
                score_tecnico = audit.get("score_tecnico", 100)
                if score_tecnico < 50:
                    score += 25
                    razones.append(f"Web en estado crítico ({score_tecnico}/100) (+25)")
                elif score_tecnico < 80:
                    score += 10
                    razones.append(f"Web con fallos técnicos ({score_tecnico}/100) (+10)")
                
                # Bonus por carga lenta específicamente
                if any("Carga lenta" in p for p in audit.get("problemas", [])):
                    score += 10
                    razones.append("Carga lenta detectada (+10)")
            
            if self._web_es_vieja(prospect.get("website", "")):
                score += 15
                razones.append("Web desactualizada detectada (+15)")

        # 2. Categoría premium (más fácil de vender)
        categoria = (prospect.get("categoria") or "").lower()
        if any(cat in categoria for cat in CATEGORIAS_PREMIUM):
            score += 20
            razones.append(f"Categoría de alto cierre: {categoria} (+20)")

        # 3. Tiene teléfono (podemos contactar)
        if prospect.get("telefono"):
            score += 10
            razones.append("Teléfono disponible (+10)")

        # 4. Tiene email (podemos contactar)
        if prospect.get("email"):
            score += 10
            razones.append("Email disponible (+10)")

        # 5. Instagram con seguidores activos (ya invierten en marketing)
        seguidores = prospect.get("seguidores", 0)
        if prospect.get("fuente") == "instagram":
            if seguidores >= 5000:
                score += 15
                razones.append(f"IG activo: {seguidores} seguidores (+15)")
            elif seguidores >= 1000:
                score += 8
                razones.append(f"IG medio: {seguidores} seguidores (+8)")

        # 6. Descripción menciona que solo usan WhatsApp (necesitan web urgente)
        descripcion = (prospect.get("descripcion") or "").lower()
        if any(señal in descripcion for señal in SEÑALES_SIN_WEB):
            score += 10
            razones.append("Solo usa WhatsApp para pedidos (+10)")

        # 7. Señales de negocio establecido (tienen presupuesto)
        if any(señal in descripcion for señal in SEÑALES_POSITIVAS):
            score += 5
            razones.append("Negocio establecido (+5)")

        # 8. Urgencia detectada (Lead FUEGO)
        if any(señal in descripcion for señal in SEÑALES_URGENCIA):
            score += 40
            razones.append("🔥 URGENCIA detectada (+40)")

        # 8. Penalizaciones
        if not prospect.get("telefono") and not prospect.get("email"):
            score -= 20
            razones.append("Sin datos de contacto (-20)")

        # Clamp score entre 0 y 100
        score = max(0, min(100, score))

        # ─── MEJORA CON CLAUDE AI (opcional) ───────────────────────
        if self.claude and score >= 40:  # Solo usa Claude para los que ya son viables
            try:
                score_ai, razon_ai = self._calificar_con_claude(prospect, score)
                score = score_ai
                razones.append(f"Análisis IA: {razon_ai}")
            except Exception as e:
                log.warning(f"Claude no disponible, usando score base: {e}")

        razon_final = " | ".join(razones) if razones else "Score base"
        log.debug(f"  Score {score}/100 para {prospect.get('nombre_negocio')}: {razon_final}")

        return score, razon_final

    def _calificar_con_claude(self, prospect: dict, score_base: int) -> Tuple[int, str]:
        """Usa Claude para análisis cualitativo adicional"""
        prompt = f"""Eres un experto en ventas de servicios web para empresas mexicanas.
Analiza este prospecto y ajusta el score de venta de 0 a 100.

DATOS DEL PROSPECTO:
- Negocio: {prospect.get('nombre_negocio')}
- Categoría: {prospect.get('categoria')}
- Ciudad: {prospect.get('ciudad')}
- Tiene web: {prospect.get('tiene_web')}
- Descripción: {prospect.get('descripcion', '')[:300]}
- Seguidores: {prospect.get('seguidores', 0)}
- Fuente: {prospect.get('fuente')}
- Score base (reglas): {score_base}

Responde SOLO en este formato JSON:
{{"score": <número 0-100>, "razon": "<una oración corta explicando el score>"}}"""

        response = self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        data = json.loads(response.content[0].text)
        return int(data["score"]), data["razon"]

    def _web_es_vieja(self, url: str) -> bool:
        """Heurística básica: algunas URLs indican sitios obsoletos"""
        if not url:
            return False
        patrones_viejos = ["blogspot", "wix.com/", "weebly", "geocities", "jimdo"]
        return any(p in url.lower() for p in patrones_viejos)

    def clasificar_servicio(self, prospect: dict) -> str:
        """Sugiere el servicio más adecuado según el perfil"""
        if not prospect.get("tiene_web"):
            return "Web desde cero"
        seguidores = prospect.get("seguidores", 0)
        if seguidores > 10000:
            return "E-commerce"
        categoria = (prospect.get("categoria") or "").lower()
        if any(c in categoria for c in ["tienda", "shop", "venta", "producto"]):
            return "E-commerce"
        return "Rediseño web"
