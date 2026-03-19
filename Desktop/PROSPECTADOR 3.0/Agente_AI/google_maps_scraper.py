import asyncio
import random
import logging
import re
import json
import httpx
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright

log = logging.getLogger("GoogleMapsScraper")

SEÑALES_EN_RESEÑAS = [
    "no tienen web", "no tienen página", "no tienen sitio",
    "no encuentro información", "no están en internet",
    "no tienen presencia online", "no aparecen en google",
    "no tiene web", "sin página web", "necesitan una web",
    "no tienen whatsapp", "solo atienden por teléfono",
    "difícil encontrarlos", "no los encuentro online",
]

def _strip_emojis(text: str) -> str:
    """Elimina emojis y caracteres especiales de un string de forma robusta."""
    if not text: return ""
    cleaned = re.sub(
        r'[\U00010000-\U0010ffff'
        r'\U0001F000-\U0001F9FF'
        r'\u2600-\u26FF'
        r'\u2700-\u27BF'
        r'\uFE00-\uFE0F]',
        '', text, flags=re.UNICODE
    )
    cleaned = cleaned.replace('\ufffd', '').strip()
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

class GoogleMapsScraper:
    def __init__(self, modo: str = "playwright", api_key: str = ""):
        self.api_key = api_key.strip() if api_key else ""
        # Si la key es un comentario o está vacía, forzar modo playwright
        if not self.api_key or self.api_key.startswith("#"):
            self.modo = "playwright"
            self.api_key = ""
        else:
            self.modo = "api"
        self._pw = None
        self.browser = None
        self.context = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self._pw:
            await self._pw.stop()

    async def _init_playwright(self):
        if self.browser:
            return True
        try:
            self._pw = await async_playwright().start()
            self.browser = await self._pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            self.context = await self.browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale="es-AR"
            )
            log.info("✅ Playwright inicializado (async)")
            return True
        except Exception as e:
            log.error(f"❌ Error inicializando Playwright: {e}")
            return False

    async def buscar(self, rubros: List[str], ciudades: List[str], solo_sin_web: bool = False, max_por_busqueda: int = 20) -> List[Dict]:
        log.info(f"🔍 Iniciando búsqueda en modo: {self.modo}")
        rubros_limpios = [_strip_emojis(r) for r in rubros if r]
        
        vistos = set()
        todos = []

        if self.modo == "playwright":
            if not await self._init_playwright():
                return []
            
            for rubro in rubros_limpios:
                for ciudad in ciudades:
                    resultados = await self._buscar_playwright(rubro, ciudad, max_por_busqueda)
                    for r in resultados:
                        key = (r["nombre_negocio"], r["telefono"])
                        if key not in vistos:
                            if not (solo_sin_web and r["tiene_web"]):
                                vistos.add(key)
                                todos.append(r)
        else:
            # Modo API
            tasks = []
            for rubro in rubros_limpios:
                for ciudad in ciudades:
                    tasks.append(self._buscar_api_single(rubro, ciudad, max_por_busqueda))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, list):
                    for r in res:
                        key = (r["nombre_negocio"], r["telefono"])
                        if key not in vistos:
                            if not (solo_sin_web and r["tiene_web"]):
                                vistos.add(key)
                                todos.append(r)
                elif isinstance(res, Exception):
                    log.error(f"Error en tarea de búsqueda API: {res}")

        log.info(f"✅ Búsqueda terminada. Total único: {len(todos)}")
        return todos

    async def _buscar_playwright(self, rubro: str, ciudad: str, max_resultados: int) -> List[Dict]:
        resultados = []
        page = await self.context.new_page()
        # Bloquear imágenes/css para velocidad
        await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())

        try:
            query = f"{rubro} en {ciudad}".replace(" ", "+")
            url = f"https://www.google.com/maps/search/{query}"
            log.info(f"🗺️ Buscando: {rubro} en {ciudad}...")
            
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)

            # Scroll más agresivo para cargar resultados
            for _ in range(5):
                await page.mouse.wheel(0, 2000)
                await asyncio.sleep(1)

            # Selectores de Google Maps actualizados (2024)
            # Intentamos varios selectores comunes para los links de los lugares
            selectors = [
                'a[href*="/maps/place/"]',
                '.hfpxzc', # Selector común de clase para los items del feed
                '[role="article"] a'
            ]
            cards = []
            for sel in selectors:
                cards = await page.query_selector_all(sel)
                if cards: break
            
            log.info(f"   {len(cards)} prospectos encontrados para {rubro} en {ciudad}")

            for card in cards[:max_resultados]:
                try:
                    nombre = await card.get_attribute("aria-label") or ""
                    href = await card.get_attribute("href") or ""
                    
                    await card.click()
                    await asyncio.sleep(1.5)

                    tel_el  = await page.query_selector('[data-tooltip="Copiar número de teléfono"]')
                    web_el  = await page.query_selector('a[data-item-id="authority"]')
                    addr_el = await page.query_selector('[data-item-id="address"]')
                    
                    telefono  = (await tel_el.inner_text()).strip() if tel_el else ""
                    website   = await web_el.get_attribute("href") if web_el else ""
                    direccion = (await addr_el.inner_text()).strip() if addr_el else ""

                    resultados.append({
                        "nombre_negocio": nombre,
                        "telefono": telefono,
                        "website": website,
                        "tiene_web": bool(website),
                        "ciudad": ciudad,
                        "categoria": rubro,
                        "fuente": "google_maps",
                        "fuente_detalle": "playwright",
                        "descripcion": direccion,
                        "perfil_url": href
                    })
                except Exception:
                    continue

        finally:
            await page.close()
        
        return resultados

    async def _buscar_api_single(self, rubro: str, ciudad: str, max_resultados: int) -> List[Dict]:
        resultados = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                query = f"{rubro} en {ciudad}"
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                params = {"query": query, "key": self.api_key, "language": "es"}
                
                resp = await client.get(url, params=params)
                data = resp.json()

                for place in data.get("results", [])[:max_resultados]:
                    place_id = place.get("place_id")
                    
                    # Detalles
                    det_url = "https://maps.googleapis.com/maps/api/place/details/json"
                    det_params = {
                        "place_id": place_id,
                        "fields": "name,formatted_phone_number,website,formatted_address,types,url",
                        "key": self.api_key,
                        "language": "es"
                    }
                    d_resp = await client.get(det_url, params=det_params)
                    p = d_resp.json().get("result", {})

                    resultados.append({
                        "nombre_negocio": p.get("name", ""),
                        "telefono": p.get("formatted_phone_number", ""),
                        "website": p.get("website", ""),
                        "tiene_web": bool(p.get("website")),
                        "ciudad": ciudad,
                        "categoria": rubro,
                        "fuente": "google_maps",
                        "fuente_detalle": "api",
                        "descripcion": p.get("formatted_address", ""),
                        "perfil_url": p.get("url", "")
                    })
        except Exception as e:
            log.error(f"Error API ({rubro}/{ciudad}): {e}")
        
        return resultados

    async def buscar_reseñas_negativas(self, ciudades: List[str], rubros: List[str]) -> List[Dict]:
        # Para simplificar el refactor, esto ahora solo usa buscar normal
        return await self.buscar(rubros, ciudades, solo_sin_web=False)
