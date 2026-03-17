"""
scraper_api.py - v2.0 OPTIMIZADO
Scraper de Google Maps con:
- Extracción de dirección, categoría, rating, reviews
- Score de oportunidad 0-100
- Link de WhatsApp directo
- Progreso en tiempo real via stderr
- Deduplicación de URLs

Uso: python scraper_api.py "agencias marketing Buenos Aires" 20
"""
import asyncio
import sys
import json
import re
import os
from playwright.async_api import async_playwright


def log(msg: str):
    """Emite progreso a stderr para que Next.js pueda capturarlo."""
    print(f"[PROGRESS] {msg}", file=sys.stderr, flush=True)


def calc_opportunity_score(data: dict) -> int:
    """
    Calcula un score de oportunidad 0-100 basado en señales del negocio.
    Mayor score = más probable que necesite nuestros servicios de IA/automatización.
    """
    score = 0

    # Sin website → necesita digitalizarse urgente (+40)
    if not data.get('website'):
        score += 40
    # Website básico (sin https, dominio gratuito, etc.) → (+20)
    elif any(x in data.get('website', '').lower() for x in ['wix', 'blogspot', 'wordpress.com', 'weebly', 'jimdo']):
        score += 20

    # Rating bajo → necesita mejorar su presencia (+20 si < 4.0 o sin rating)
    rating_str = data.get('rating', '')
    if not rating_str:
        score += 10  # Sin reseñas = negocio nuevo o invisible
    else:
        try:
            rating = float(rating_str.replace(',', '.'))
            if rating < 4.0:
                score += 20
            elif rating < 4.5:
                score += 10
        except:
            score += 5

    # Pocas reseñas → negocio pequeño, más receptivo (+15)
    reviews_str = data.get('reviews', '')
    if reviews_str:
        try:
            reviews = int(re.sub(r'[^\d]', '', reviews_str))
            if reviews < 10:
                score += 15
            elif reviews < 50:
                score += 8
        except:
            pass
    else:
        score += 10

    # Tiene teléfono → podemos contactar (+15)
    if data.get('phone'):
        score += 15

    return min(score, 100)


def format_phone_argentina(raw: str) -> str:
    """Normaliza un número a formato internacional argentino."""
    clean = re.sub(r'[^\d+]', '', raw)
    if clean.startswith('+'):
        return clean
    if clean.startswith('0'):
        return '+549' + clean[1:]
    if clean.startswith('11') or clean.startswith('15'):
        return '+549' + clean
    if len(clean) == 8:
        return '+5491l' + clean  # BA fixedline fallback
    return clean


async def scrape(search_query: str, max_results: int = 20):
    leads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale='es-ES',
            geolocation={'longitude': -58.3816, 'latitude': -34.6037},  # Buenos Aires
            permissions=['geolocation']
        )
        page = await context.new_page()

        log(f"Iniciando búsqueda: {search_query}")
        search_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Aceptar cookies si aparece
        try:
            await page.click('button:has-text("Aceptar todo")', timeout=3000)
        except:
            pass

        # Scroll para cargar resultados
        log("Cargando resultados...")
        try:
            await page.wait_for_selector('a[href^="https://www.google.com/maps/place"]', timeout=10000)
            for i in range(8):
                await page.mouse.wheel(delta_x=0, delta_y=10000)
                await asyncio.sleep(1.5)
        except:
            pass

        # Obtener URLs únicas
        urls = []
        links = await page.query_selector_all('a[href^="https://www.google.com/maps/place"]')
        for link in links:
            href = await link.get_attribute('href')
            if href and href not in urls:
                urls.append(href)
                if len(urls) >= max_results:
                    break

        log(f"Encontrados {len(urls)} negocios. Extrayendo datos...")

        # Extraer datos de cada lugar
        for idx, url in enumerate(urls):
            log(f"Procesando {idx + 1}/{len(urls)}...")
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await asyncio.sleep(2)

                data = {
                    'nombre': '',
                    'phone': '',
                    'website': '',
                    'address': '',
                    'category': '',
                    'rating': '',
                    'reviews': '',
                    'busqueda': search_query,
                    'maps_url': url,
                }

                # Nombre
                try:
                    el = await page.query_selector('h1')
                    data['nombre'] = (await el.inner_text()).strip() if el else ''
                except:
                    pass

                # Categoría (aparece debajo del nombre)
                try:
                    cat_el = await page.query_selector('button[jsaction*="category"]')
                    if not cat_el:
                        cat_el = await page.query_selector('button.DkEaL')
                    if cat_el:
                        data['category'] = (await cat_el.inner_text()).strip()
                except:
                    pass

                # Dirección
                try:
                    addr_els = await page.query_selector_all('button[data-item-id^="address"]')
                    if addr_els:
                        data['address'] = (await addr_els[0].inner_text()).strip()
                    else:
                        # Fallback: aria-label con "Dirección"
                        addr_el2 = await page.query_selector('[data-tooltip="Copiar dirección"]')
                        if addr_el2:
                            data['address'] = (await addr_el2.inner_text()).strip()
                except:
                    pass

                # Teléfono
                try:
                    phone_els = await page.query_selector_all('button[data-item-id^="phone:tel:"]')
                    if phone_els:
                        raw = (await phone_els[0].inner_text()).strip()
                        data['phone'] = format_phone_argentina(raw)
                except:
                    pass

                # Website
                try:
                    links_page = await page.query_selector_all('a[href^="http"]')
                    for l in links_page:
                        href = await l.get_attribute('href')
                        if href and 'google.com' not in href and 'gstatic.com' not in href:
                            data['website'] = href
                            break
                except:
                    pass

                # Rating
                try:
                    rating_el = await page.query_selector('div[aria-label*="estrellas"]')
                    if rating_el:
                        aria = await rating_el.get_attribute('aria-label')
                        data['rating'] = aria.split(' ')[0] if aria else ''
                except:
                    pass

                # Reviews
                try:
                    rev_el = await page.query_selector('button[aria-label*="reseñas"]')
                    if rev_el:
                        data['reviews'] = re.sub(r'[^\d]', '', await rev_el.inner_text())
                except:
                    pass

                # Calcular score y generar link de WhatsApp
                data['opportunity_score'] = calc_opportunity_score(data)
                data['whatsapp_link'] = f"https://wa.me/{data['phone'].replace('+', '')}" if data['phone'] else ''

                # Solo guardar si tiene nombre (mínimo dato útil)
                if data['nombre']:
                    leads.append(data)

                await asyncio.sleep(1.5)

            except Exception as e:
                log(f"Error en {url}: {e}")
                continue

        await browser.close()

    log(f"Completado. {len(leads)} leads extraídos.")
    return leads


async def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "agencias de marketing Buenos Aires"
    max_r = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    leads = await scrape(query, max_r)
    
    # --- Persistence Logic ---
    output_dir = os.path.join(os.path.dirname(__file__), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "leads.json")
    
    existing_leads = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing_leads = json.load(f)
        except:
            pass
            
    # Merge and deduplicate by maps_url
    merged_leads = {lead['maps_url']: lead for lead in existing_leads}
    for lead in leads:
        merged_leads[lead['maps_url']] = lead
        
    final_leads = list(merged_leads.values())
    
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(final_leads, f, ensure_ascii=False, indent=2)
        log(f"✅ {len(leads)} leads nuevos (Total: {len(final_leads)}) guardados en {filepath}")
    except Exception as e:
        log(f"❌ Error al guardar leads: {e}")
    # -------------------------

    # JSON limpio a stdout para compatibilidad
    print(json.dumps(leads, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
