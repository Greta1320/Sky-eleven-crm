"""
Scraper Adapter COMPLETO — SKY Eleven
=======================================
Integra los 4 canales: Google Maps, Instagram, LinkedIn, Reseñas.
Lee la configuración del dashboard y ejecuta cada canal.

Configurar en .env:
    # Google Maps
    GOOGLE_MAPS_MODO=playwright          # "playwright" o "api"
    GOOGLE_MAPS_API_KEY=                 # Solo si usás modo "api"

    # Instagram
    INSTAGRAM_USUARIO=tu_usuario
    INSTAGRAM_PASSWORD=tu_password
    INSTAGRAM_CUENTAS_DIRECTORIO=timeout_buenosaires,donde_ir_bsas

    # LinkedIn
    LINKEDIN_EMAIL=tucuenta@gmail.com
    LINKEDIN_PASSWORD=tu_password
"""

import logging
import json
import os
import asyncio
from typing import List, Dict, Any
from config import Config

log = logging.getLogger("ScraperAdapter")


class ScraperAdapter:
    def __init__(self, config: Config):
        self.config = config
        self._cargar_configuracion_dashboard()

    def _cargar_configuracion_dashboard(self):
        """Carga la config guardada desde el dashboard (localStorage → archivo)"""
        try:
            from google_maps_scraper import _strip_emojis
        except ImportError:
            import re as _re
            def _strip_emojis(t): return _re.sub(r'[^\x00-\x7F\u00C0-\u024F ]', '', t).strip()

        config_path = "sky_config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, encoding="utf-8", errors="replace") as f:
                    cfg = json.load(f)
            except Exception as e:
                log.error(f"Error leyendo sky_config.json: {e}. Usando defaults.")
                cfg = {}

            rubros_raw   = cfg.get("rubros", [])
            ciudades_raw = cfg.get("ciudades", "CABA, GBA Norte")

            # Strip emojis de forma robusta (también maneja encoding corrupto con \ufffd)
            self.rubros   = [_strip_emojis(r) for r in rubros_raw if _strip_emojis(r)]
            self.ciudades = [c.strip() for c in ciudades_raw.split(",") if c.strip()]
            self.canales  = cfg.get("canales", ["google_maps", "instagram", "linkedin"])
        else:
            # Defaults si no hay config del dashboard
            self.rubros   = ["restaurantes", "clínicas dentales", "abogados", "spas / estéticas"]
            self.ciudades = ["CABA", "GBA Norte"]
            self.canales  = ["google_maps", "instagram", "linkedin", "reviews"]

        log.info("Configuración cargada:")
        log.info(f"  Rubros:   {self.rubros}")
        log.info(f"  Ciudades: {self.ciudades}")
        log.info(f"  Canales:  {self.canales}")


    async def scrape(self, canal: str) -> List[Dict[str, Any]]:
        """Enruta al scraper correcto"""
        handlers = {
            "google_maps": self._scrape_google_maps,
            "instagram":   self._scrape_instagram,
            "linkedin":    self._scrape_linkedin,
            "reviews":     self._scrape_reseñas,
        }
        handler = handlers.get(canal)
        if not handler:
            log.warning(f"Canal desconocido: {canal}")
            return []

        if canal not in self.canales:
            log.info(f"Canal {canal} desactivado en configuración")
            return []

        return await handler()

    # ── GOOGLE MAPS ───────────────────────────────────────────────────────────
    async def _scrape_google_maps(self) -> List[Dict]:
        log.info("🗺️ Iniciando Google Maps scraper...")
        try:
            from google_maps_scraper import GoogleMapsScraper

            modo    = os.getenv("GOOGLE_MAPS_MODO", "playwright")
            api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

            async with GoogleMapsScraper(modo=modo, api_key=api_key) as scraper:
                raw = await scraper.buscar(
                    rubros=self.rubros,
                    ciudades=self.ciudades,
                    solo_sin_web=False,
                    max_por_busqueda=20,
                )
            return [self._normalizar(r, "google_maps") for r in raw]

        except Exception as e:
            log.error(f"Error Google Maps: {e}")
            return []

    # ── INSTAGRAM ─────────────────────────────────────────────────────────────
    async def _scrape_instagram(self) -> List[Dict]:
        log.info("📸 Iniciando Instagram scraper...")
        try:
            from instagram_scraper import InstagramScraper

            usuario  = os.getenv("INSTAGRAM_USUARIO", "")
            password = os.getenv("INSTAGRAM_PASSWORD", "")

            if not usuario or not password:
                log.warning("⚠️ Configurar INSTAGRAM_USUARIO y INSTAGRAM_PASSWORD en .env")
                return []

            cuentas_dir_str = os.getenv("INSTAGRAM_CUENTAS_DIRECTORIO", "")
            cuentas_directorio = [c.strip() for c in cuentas_dir_str.split(",") if c.strip()]

            scraper = InstagramScraper(
                usuario=usuario,
                password=password,
                delay_min=30,   # Mínimo 30s entre acciones
                delay_max=90,   # Máximo 90s (anti-baneo)
            )
            raw = await asyncio.to_thread(
                scraper.buscar_todo,
                rubros=self.rubros,
                ciudades=self.ciudades,
                cuentas_directorio=cuentas_directorio or None,
            )
            return [self._normalizar(r, "instagram") for r in raw]

        except Exception as e:
            log.error(f"Error Instagram: {e}")
            return []

    # ── LINKEDIN ──────────────────────────────────────────────────────────────
    async def _scrape_linkedin(self) -> List[Dict]:
        log.info("💼 Iniciando LinkedIn scraper...")
        try:
            from linkedin_scraper import LinkedInScraper

            email    = os.getenv("LINKEDIN_EMAIL", "")
            password = os.getenv("LINKEDIN_PASSWORD", "")

            if not email or not password:
                log.warning("⚠️ Configurar LINKEDIN_EMAIL y LINKEDIN_PASSWORD en .env")
                return []

            scraper = LinkedInScraper(
                email=email,
                password=password,
                delay_min=5,
                delay_max=20,
            )
            raw = await asyncio.to_thread(
                scraper.buscar_todo,
                rubros=self.rubros,
                ciudades=self.ciudades,
            )

            # LinkedIn es especial: atacamos por 3 canales con cada lead
            resultados = []
            for r in raw:
                normalizado = self._normalizar(r, "linkedin")
                normalizado["canales_disponibles"] = []
                if normalizado.get("email"):
                    normalizado["canales_disponibles"].append("email")
                if normalizado.get("telefono"):
                    normalizado["canales_disponibles"].append("whatsapp")
                normalizado["canales_disponibles"].append("linkedin_dm")
                resultados.append(normalizado)

            return resultados

        except Exception as e:
            log.error(f"Error LinkedIn: {e}")
            return []

    # ── RESEÑAS NEGATIVAS ─────────────────────────────────────────────────────
    async def _scrape_reseñas(self) -> List[Dict]:
        log.info("⭐ Buscando reseñas negativas (señal de que necesitan web)...")
        try:
            from google_maps_scraper import GoogleMapsScraper

            modo    = os.getenv("GOOGLE_MAPS_MODO", "playwright")
            api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")

            async with GoogleMapsScraper(modo=modo, api_key=api_key) as scraper:
                raw = await scraper.buscar_reseñas_negativas(
                    ciudades=self.ciudades,
                    rubros=self.rubros,
                )
            # Marcar con score extra por señal
            resultados = []
            for r in raw:
                n = self._normalizar(r, "reviews")
                n["score_extra"] = 20  # Bonus por señal en reseña
                n["fuente"] = "reseñas"
                resultados.append(n)
            return resultados

        except Exception as e:
            log.error(f"Error reseñas: {e}")
            return []

    # ── NORMALIZAR ────────────────────────────────────────────────────────────
    def _normalizar(self, raw: dict, fuente: str) -> Dict[str, Any]:
        """Asegura que todos los campos obligatorios existan"""
        return {
            "nombre_negocio": raw.get("nombre_negocio", ""),
            "contacto":       raw.get("contacto", ""),
            "telefono":       self._limpiar_telefono(raw.get("telefono", "")),
            "email":          raw.get("email", "").strip().lower(),
            "website":        raw.get("website", ""),
            "tiene_web":      bool(raw.get("tiene_web", False)),
            "ciudad":         raw.get("ciudad", ""),
            "categoria":      raw.get("categoria", ""),
            "fuente":         raw.get("fuente", fuente),
            "fuente_detalle": raw.get("fuente_detalle", ""),
            "perfil_url":     raw.get("perfil_url", ""),
            "seguidores":     int(raw.get("seguidores", 0)),
            "descripcion":    raw.get("descripcion", ""),
            "score_extra":    int(raw.get("score_extra", 0)),
            "raw_data":       raw.get("raw_data", raw),
        }

    def _limpiar_telefono(self, tel: str) -> str:
        """Normaliza teléfono a formato 549XXXXXXXXXX"""
        if not tel:
            return ""
        # Quitar todo excepto números
        numeros = re.sub(r'\D', '', tel)
        if not numeros:
            return ""
        # Agregar prefijo Argentina si no tiene
        if numeros.startswith("549"):
            return numeros
        if numeros.startswith("54"):
            return "549" + numeros[2:] if not numeros.startswith("549") else numeros
        if numeros.startswith("0"):
            numeros = numeros[1:]
        if numeros.startswith("9"):
            return "54" + numeros
        return "549" + numeros


import re  # mover al top en producción
