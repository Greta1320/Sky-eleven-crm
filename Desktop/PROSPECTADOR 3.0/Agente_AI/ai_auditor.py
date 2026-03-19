import asyncio
import logging
from playwright.async_api import async_playwright
import time

log = logging.getLogger("AIAuditor")

class AIAuditor:
    """
    Analiza sitios web de prospectos para encontrar 'dolores' técnicos.
    - Velocidad de carga
    - SEO básico (Meta tags)
    - Responsividad (Mobile)
    - Presencia de Píxeles (FB, Google)
    """
    
    def __init__(self):
        self.results = {}

    async def auditar(self, url: str) -> dict:
        if not url or not url.startswith("http"):
            return {"score": 0, "problemas": ["URL inválida"]}

        log.info(f"🧐 Auditando: {url}")
        
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                start_time = time.time()
                response = await page.goto(url, timeout=30000, wait_until="load")
                load_time = time.time() - start_time
                
                # 1. Velocidad
                slow_load = load_time > 4.0
                
                # 2. SEO
                title = await page.title()
                has_meta_desc = await page.query_selector('meta[name="description"]')
                
                # 3. Mobile friendly (check viewport meta)
                has_viewport = await page.query_selector('meta[name="viewport"]')
                
                # 4. Pixel tracking
                content = await page.content()
                has_pixel = "fbevents.js" in content or "gtag" in content
                
                # 5. Contact Extraction (Regex)
                contactos = self._buscar_contactos(content)
                
                problemas = []
                puntos = 100
                
                if slow_load:
                    problemas.append(f"Carga lenta ({load_time:.1f}s)")
                    puntos -= 30
                if not has_meta_desc:
                    problemas.append("Falta meta-descripción SEO")
                    puntos -= 15
                if not has_viewport:
                    problemas.append("No optimizada para móviles")
                    puntos -= 25
                if not has_pixel:
                    problemas.append("No tiene tracking de anuncios (FB/Google)")
                    puntos -= 10
                
                await browser.close()
                
                return {
                    "url": url,
                    "score_tecnico": puntos,
                    "load_time": f"{load_time:.1f}s",
                    "problemas": problemas,
                    "gancho_venta": self._generar_gancho(problemas),
                    "telefono": contactos.get("telefono"),
                    "email": contactos.get("email")
                }
            except Exception as e:
                log.error(f"Error auditando {url}: {e}")
                return {"error": str(e), "score": 0}

    def _buscar_contactos(self, html: str) -> dict:
        """Busca teléfonos y emails en el HTML usando regex"""
        import re
        resultado = {"telefono": None, "email": None}
        
        # Email: regex simple
        emails = re.findall(r'[a-zA-Z0-9-._]+@[a-zA-Z0-9-._]+\.[a-zA-Z]{2,}', html)
        if emails:
            # Filtrar dominios comunes de imágenes/assets si es necesario
            validos = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]
            if validos:
                resultado["email"] = validos[0].lower()

        # Teléfono: regex para formatos latinos (Argentina/México)
        # Busca patrones como +54 9 11..., 11-4444-5555, etc.
        tel_match = re.search(r'(\+?54\s?9?\s?11\s?\d{4}\s?\d{4}|0?\s?(?:11|[2-9]\d{2,3})\s*[\s\-]?\d{4}[\s\-]?\d{4})', html)
        if tel_match:
            resultado["telefono"] = tel_match.group(0).strip()
            
        return resultado

    def _generar_gancho(self, problemas: list) -> str:
        if not problemas:
            return "¡Tu web tiene una base sólida! Me gustaría mostrarte cómo podemos potenciarla con un embudo de ventas automatizado para escalar tus resultados."
        
        # Mapear problemas a frases de impacto
        impacto = []
        if any("lenta" in p for p in problemas):
            impacto.append("tu web tarda demasiado en cargar y hoy estás perdiendo clientes que no esperan")
        if any("SEO" in p for p in problemas):
            impacto.append("no te están encontrando en Google por falta de etiquetas SEO críticas")
        if any("móviles" in p for p in problemas):
            impacto.append("tu web no se ve bien en celulares, donde hoy ocurre el 80% de las búsquedas")
        if any("tracking" in p for p in problemas):
            impacto.append("no estás midiendo quién entra a tu web, lo cual es dinero tirado a la basura")
        
        frase = " | ".join(impacto[:2])
        if not frase:
            frase = ", ".join(problemas[:2])

        return f"Hola! Analicé tu sitio y noté algo crítico: {frase}. ¿Te gustaría que lo solucionemos para subir tus ventas?"

if __name__ == "__main__":
    # Test simple
    async def test():
        auditor = AIAuditor()
        res = await auditor.auditar("https://www.google.com")
        print(res)
    
    asyncio.run(test())
