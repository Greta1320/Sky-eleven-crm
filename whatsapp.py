"""
WhatsApp via Evolution API — SKY Eleven
========================================
Envía notificaciones a tu número cuando llega un prospecto HOT
y mensajes de primer contacto / seguimiento a los prospectos.
"""

import logging
import httpx
from typing import Dict, Any
from config import Config

log = logging.getLogger("WhatsApp")


class WhatsAppNotifier:
    def __init__(self, config: Config):
        self.config = config
        self.base_url = f"{config.EVOLUTION_API_URL}/message/sendText/{config.EVOLUTION_INSTANCE}"
        self.headers = {
            "Content-Type": "application/json",
            "apikey": config.EVOLUTION_API_KEY,
        }

    async def _enviar(self, numero: str, mensaje: str) -> bool:
        """
        Envía un mensaje vía Evolution API.
        
        Evolution API espera:
        POST /message/sendText/{instance}
        { "number": "521XXXXXXXXXX", "text": "Hola..." }
        """
        numero_limpio = self._limpiar_numero(numero)
        if not numero_limpio:
            log.warning("Número inválido, no se envió WA")
            return False

        payload = {
            "number": numero_limpio,
            "text":   mensaje,
            "delay":  1200   # delay en ms para parecer más humano
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(self.base_url, json=payload, headers=self.headers)
                resp.raise_for_status()
                log.info(f"✅ WA enviado a {numero_limpio}")
                return True
        except httpx.HTTPStatusError as e:
            log.error(f"❌ Error HTTP WA ({e.response.status_code}): {e.response.text}")
        except httpx.RequestError as e:
            log.error(f"❌ Error de red WA: {e}")
        return False

    async def notificar_prospecto(self, prospect: Dict[str, Any]) -> bool:
        """
        Notifica A TI (dueño de SKY Eleven) sobre un nuevo prospecto HOT.
        Se manda a tu número de WhatsApp configurado.
        """
        mensaje = self.config.TEMPLATE_WSP_ALERTA.format(
            nombre_negocio = prospect.get("nombre_negocio", "—"),
            contacto       = prospect.get("contacto", "—"),
            ciudad         = prospect.get("ciudad", "—"),
            fuente         = prospect.get("fuente", "—"),
            score          = prospect.get("score", 0),
            servicio       = prospect.get("servicio", "Web"),
            telefono       = prospect.get("telefono", "—"),
            email          = prospect.get("email", "—"),
            razon_score    = prospect.get("razon_score", "—"),
            crm_link       = f"http://localhost:5000/crm/{prospect.get('id', '')}",
        )

        return await self._enviar(self.config.WSP_NUMERO_DESTINO, mensaje)

    async def contactar_prospecto(self, prospect: Dict[str, Any]) -> bool:
        """
        Envía mensaje de primer contacto DIRECTAMENTE al prospecto.
        Solo si WSP_CONTACTAR_CLIENTE = True en config.
        """
        if not self.config.WSP_NUMERO_CLIENTE:
            log.info("Contacto directo a prospectos deshabilitado")
            return False

        if not prospect.get("telefono"):
            log.warning(f"Sin teléfono para {prospect.get('nombre_negocio')}")
            return False

        mensaje = self.config.TEMPLATE_DM_INSTAGRAM.format(
            contacto       = prospect.get("contacto") or "amig@",
            nombre_negocio = prospect.get("nombre_negocio", ""),
        )

        return await self._enviar(prospect["telefono"], mensaje)

    async def enviar_seguimiento(self, prospect: Dict[str, Any]) -> bool:
        """Envía mensaje de seguimiento al prospecto que no respondió"""
        if not prospect.get("telefono"):
            return False

        mensaje = self.config.TEMPLATE_SEGUIMIENTO.format(
            contacto       = prospect.get("contacto") or "amig@",
            nombre_negocio = prospect.get("nombre_negocio", ""),
        )

        return await self._enviar(prospect["telefono"], mensaje)

    async def enviar_resumen_diario(self, stats: Dict) -> bool:
        """
        Envía resumen diario de actividad del agente a tu WhatsApp.
        Llámalo a las 9am o al finalizar el día.
        """
        total      = stats.get("total", 0)
        por_etapa  = stats.get("por_etapa", {})
        hot        = stats.get("hot", 0)

        resumen = f"""📊 *RESUMEN DIARIO — SKY Eleven Agent*
━━━━━━━━━━━━━━━━━━━━━━
📋 Total prospectos: *{total}*
🔥 HOT (score ≥70): *{hot}*

*Por etapa:*
{chr(10).join(f'  • {k}: {v}' for k, v in por_etapa.items())}

⏰ Siguiente ciclo en {self._proxima_hora()} hrs
🤖 _SKY Eleven Agent activo_"""

        return await self._enviar(self.config.WSP_NUMERO_DESTINO, resumen)

    def _limpiar_numero(self, numero: str) -> str:
        """
        Limpia y formatea el número para Evolution API.
        Evolution API espera formato: 521XXXXXXXXXX (sin +, con código de país)
        """
        if not numero:
            return ""
        # Elimina todo excepto dígitos
        limpio = "".join(c for c in numero if c.isdigit())
        # Si empieza con 52 (México) o 54 (Argentina), dejarlo así
        if limpio.startswith("52") or limpio.startswith("54") or limpio.startswith("1"):
            return limpio
        # Si empieza con 0, probablemente local → agregar 52
        if limpio.startswith("0"):
            limpio = "52" + limpio[1:]
        # Si tiene 10 dígitos (México sin código), agregar 52
        if len(limpio) == 10:
            limpio = "52" + limpio
        return limpio

    def _proxima_hora(self) -> int:
        from datetime import datetime
        return 6  # Placeholder — el scheduler lo maneja
