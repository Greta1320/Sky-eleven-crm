"""
SKY Eleven - Agente Autónomo de Prospección
============================================
Orquesta: Scraper → Calificador IA → CRM → WhatsApp (Evolution API)
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime
from typing import List

from scraper_adapter import ScraperAdapter
from qualifier import ProspectQualifier
from crm_integration import CRMIntegration
from whatsapp import WhatsAppNotifier
from config import Config

from logger_utils import setup_logging
log = setup_logging("bot.log")
log = logging.getLogger("SKYAgent")


class SkyElevenAgent:
    def __init__(self):
        self.config = Config()
        self.scraper   = ScraperAdapter(self.config)
        self.qualifier = ProspectQualifier(self.config)
        self.crm       = CRMIntegration(self.config)
        self.whatsapp  = WhatsAppNotifier(self.config)
        self.stats     = {"scraped": 0, "qualified": 0, "notified": 0, "skipped": 0}

    async def run_cycle(self):
        """Un ciclo completo del agente: scrape → califica → guarda → notifica"""
        log.info("=" * 60)
        log.info(f"🚀 CICLO INICIADO — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. SCRAPING de todos los canales configurados
        raw_prospects = []
        for canal in self.config.CANALES_ACTIVOS:
            log.info(f"🔍 Scrapeando canal: {canal}")
            try:
                resultados = await self.scraper.scrape(canal)
                raw_prospects.extend(resultados)
                log.info(f"   ✅ {len(resultados)} negocios encontrados en {canal}")
            except Exception as e:
                log.error(f"   ❌ Error en {canal}: {e}")

        self.stats["scraped"] += len(raw_prospects)
        log.info(f"📊 Total scraped este ciclo: {len(raw_prospects)}")

        # 2. FILTRAR duplicados contra CRM
        nuevos = await self.crm.filtrar_duplicados(raw_prospects)
        log.info(f"🔄 Nuevos (sin duplicados): {len(nuevos)}")

        if not nuevos:
            log.info("⏭️  Sin prospectos nuevos. Fin del ciclo.")
            return

        # 3. CALIFICAR con IA
        calificados = []
        for prospect in nuevos:
            score, razon = self.qualifier.calificar(prospect)
            prospect["score"]        = score
            prospect["razon_score"]  = razon
            prospect["stage"]        = "Nuevo"
            prospect["fecha"]        = datetime.now().isoformat()
            calificados.append(prospect)

        self.stats["qualified"] += len(calificados)

        # 4. GUARDAR en CRM (tu DB existente)
        guardados = await self.crm.guardar_prospectos(calificados)
        log.info(f"💾 Guardados en CRM: {len(guardados)}")

        # 5. NOTIFICAR por WhatsApp los que superan el umbral
        hot_prospects = [p for p in guardados if p["score"] >= self.config.SCORE_MINIMO_WSP]
        log.info(f"🔥 Prospectos HOT (score ≥ {self.config.SCORE_MINIMO_WSP}): {len(hot_prospects)}")

        for prospect in hot_prospects:
            try:
                await self.whatsapp.notificar_prospecto(prospect)
                await self.crm.marcar_notificado(prospect["id"])
                self.stats["notified"] += 1
                log.info(f"   📱 WhatsApp enviado: {prospect['nombre_negocio']} (score: {prospect['score']})")
                await asyncio.sleep(3)  # Evitar spam en WA
            except Exception as e:
                log.error(f"   ❌ Error WA para {prospect.get('nombre_negocio')}: {e}")

        # 6. REPORTE del ciclo
        skipped = len(raw_prospects) - len(nuevos)
        self.stats["skipped"] += skipped
        self._log_resumen(len(raw_prospects), len(nuevos), len(hot_prospects))

    def _log_resumen(self, scraped, nuevos, notificados):
        log.info("─" * 60)
        log.info(f"📈 RESUMEN DEL CICLO:")
        log.info(f"   Scraped:     {scraped}")
        log.info(f"   Nuevos:      {nuevos}")
        log.info(f"   Notificados: {notificados}")
        log.info(f"   Total acum.  Scraped={self.stats['scraped']} | Notificados={self.stats['notified']}")
        log.info("=" * 60)

    async def seguimiento_automatico(self):
        """Envía seguimiento a prospectos que no han respondido en X días"""
        log.info("📬 Iniciando seguimiento automático...")
        sin_respuesta = await self.crm.obtener_sin_respuesta(dias=self.config.DIAS_SEGUIMIENTO)
        
        for prospect in sin_respuesta:
            await self.whatsapp.enviar_seguimiento(prospect)
            await self.crm.registrar_seguimiento(prospect["id"])
            log.info(f"   🔁 Seguimiento enviado: {prospect['nombre_negocio']}")
            await asyncio.sleep(5)

    def iniciar(self):
        """Inicia el agente con el scheduler"""
        log.info("🤖 SKY Eleven Agent INICIANDO...")
        log.info(f"   Canales: {self.config.CANALES_ACTIVOS}")
        log.info(f"   Ciclo cada: {self.config.INTERVALO_HORAS}h")
        log.info(f"   Score mínimo WA: {self.config.SCORE_MINIMO_WSP}")

        # Ejecutar inmediatamente al iniciar
        asyncio.run(self.run_cycle())

        # Programar ciclos recurrentes
        schedule.every(self.config.INTERVALO_HORAS).hours.do(
            lambda: asyncio.run(self.run_cycle())
        )
        schedule.every().day.at("09:00").do(
            lambda: asyncio.run(self.seguimiento_automatico())
        )

        log.info("⏰ Scheduler activo. Esperando próximo ciclo...")
        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    agent = SkyElevenAgent()
    agent.iniciar()
