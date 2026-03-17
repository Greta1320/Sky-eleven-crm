import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import time
import re
import os

class GoogleMapsScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.leads = []

    async def _scroll_results(self, page):
        """Hace scroll en el panel lateral para cargar más resultados."""
        print("Haciendo scroll para cargar resultados...")
        
        # El panel lateral de resultados de Google Maps
        # Tenemos que encontrar el contendor scrolleable correcto
        try:
            # Esperar a que cargue el primer resultado
            await page.wait_for_selector('a[href^="https://www.google.com/maps/place"]', timeout=10000)
            
            # Selector heurístico del contenedor de scroll (suele cambiar)
            scroll_container_xpath = '//div[contains(@aria-label, "Resultados de ")]'
            
            # Hacer scroll unas cuantas veces
            for _ in range(5):
                await page.mouse.wheel(delta_x=0, delta_y=10000)
                await asyncio.sleep(2)
                
            print("Scroll completado.")
        except Exception as e:
            print(f"Error o fin del scroll: {e}")

    async def _extract_place_data(self, page, url):
        """Extrae los detalles de un lugar específico."""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2) # Espera a que carguen los datos del panel
            
            # Nombre
            try:
                name_element = await page.query_selector('h1')
                name = await name_element.inner_text() if name_element else ""
            except:
                name = ""

            # Website
            website = ""
            try:
                # Busca enlaces que parezcan de website (ignora enlaces internos de google)
                links = await page.query_selector_all('a[href^="http"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and 'google.com' not in href and 'gstatic.com' not in href:
                        website = href
                        break
            except:
                pass

            # Teléfono
            phone = ""
            try:
                phone_elements = await page.query_selector_all('button[data-tooltip*="Copiar el número de teléfono"]')
                if not phone_elements:
                    phone_elements = await page.query_selector_all('button[data-item-id^="phone:tel:"]')
                
                if phone_elements:
                    phone_text = await phone_elements[0].inner_text()
                    # Limpiar y formatear número (asumiendo Argentina temporalmente para la demo)
                    raw_phone = re.sub(r'[^\d+]', '', phone_text)
                    if not raw_phone.startswith('+'):
                        # Si inicia con 0 (larga distancia nacional), sacamos el 0 y agregamos +549
                        if raw_phone.startswith('0'):
                            phone = '+549' + raw_phone[1:]
                        # Si es número de bs as sin 0
                        elif raw_phone.startswith('11'):
                            phone = '+549' + raw_phone
                        else:
                            phone = raw_phone
                    else:
                        phone = raw_phone
            except:
                pass

            # Rating y Reviews (opcional, sirve para contexto)
            rating = ""
            reviews = ""
            try:
                rating_elem = await page.query_selector('div[aria-label*="estrellas"]')
                if rating_elem:
                    aria_label = await rating_elem.get_attribute('aria-label')
                    rating = aria_label.split(' ')[0] if aria_label else ""
                    
                reviews_elem = await page.query_selector('button[aria-label*="reseñas"]')
                if reviews_elem:
                    reviews_text = await reviews_elem.inner_text()
                    reviews = re.sub(r'[^\d]', '', reviews_text)
            except:
                pass

            return {
                "nombre": name.strip(),
                "telefono": phone.strip(),
                "website": website.strip(),
                "rating": rating,
                "reviews": reviews,
                "url_maps": url
            }
        except Exception as e:
            print(f"Error extrayendo datos de {url}: {e}")
            return None

    async def scrape(self, search_query, max_results=20):
        print(f"Iniciando búsqueda: {search_query}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                locale='es-ES',
                geolocation={'longitude': -3.703790, 'latitude': 40.416775}, # Ejemplo: Madrid
                permissions=['geolocation']
            )
            page = await context.new_page()

            # Búsqueda por URL directa es más confiable
            search_url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(5) # Dar tiempo extra a que renderice la UI
            
            # Aceptar cookies si aparece
            try:
                await page.click('button:has-text("Aceptar todo")', timeout=3000)
            except:
                pass
            
            # Esperar resultados y hacer scroll
            await self._scroll_results(page)

            # Obtener URLs de los resultados
            urls = []
            links = await page.query_selector_all('a[href^="https://www.google.com/maps/place"]')
            for link in links:
                href = await link.get_attribute('href')
                if href and href not in urls:
                    urls.append(href)
                    if len(urls) >= max_results:
                        break
            
            print(f"Se encontraron {len(urls)} enlaces. Extrañendo detalles...")

            # Extraer detalles de cada URL
            for i, url in enumerate(urls):
                print(f"Procesando {i+1}/{len(urls)}...")
                data = await self._extract_place_data(page, url)
                if data and data['nombre']:
                    # Scoring simple inicial
                    oportunidad = 0
                    if not data['website']:
                        oportunidad += 10
                    if data['telefono']:
                        oportunidad += 5
                    
                    data['oportunidad_score'] = oportunidad
                    data['busqueda'] = search_query
                    
                    self.leads.append(data)
                
                # Pausa para no saturar el servidor
                await asyncio.sleep(2)

            await browser.close()
            
        return self.leads

    def save_to_csv(self, filename="leads.csv"):
        if not self.leads:
            print("No hay leads para guardar.")
            return

        df = pd.DataFrame(self.leads)
        
        # Limpieza final
        df['website'] = df['website'].fillna('NO TIENE')
        df['telefono'] = df['telefono'].fillna('')
        
        # Formatear IDs únicos
        df['id_lead'] = df.index + 1
        
        # Guardar
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"✅ {len(self.leads)} leads guardados en {filepath}")
        return filepath

# Ejecutar test local
async def main():
    # Inicializar scraper (headless=False por ahora para ver qué hace)
    scraper = GoogleMapsScraper(headless=False)
    
    # Buscar
    query = "inmobiliarias en florida buenos aires"
    leads = await scraper.scrape(query, max_results=5) # 5 leads para probar rápido
    
    # Guardar
    scraper.save_to_csv("test_leads.csv")

if __name__ == "__main__":
    asyncio.run(main())
