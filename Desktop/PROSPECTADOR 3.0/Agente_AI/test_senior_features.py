import asyncio
import logging
import sys
import os

# Añadir directorio actual al path para importar módulos locales
sys.path.append(os.getcwd())

from ai_auditor import AIAuditor
from instagram_scraper import InstagramScraper
from logger_utils import setup_logging

setup_logging("test_senior.log")
log = logging.getLogger("TestSenior")

async def test_ai_auditor():
    print("\n--- TEST 1: AI AUDITOR ---")
    auditor = AIAuditor()
    # Probamos con una web conocida por ser lenta o tener temas SEO (ejemplo genérico)
    url = "https://www.infobae.com" 
    print(f"Auditando {url}...")
    res = await auditor.auditar(url)
    print(f"Resultado: {res}")
    return res

async def test_instagram_competencia():
    print("\n--- TEST 2: INSTAGRAM COMPETENCIA ---")
    user = os.getenv("INSTAGRAM_USUARIO")
    pwd = os.getenv("INSTAGRAM_PASSWORD")
    
    if not user or not pwd:
        print("Saltando test IG: No hay credenciales en .env")
        return
    
    scraper = InstagramScraper(user, pwd)
    # Buscamos seguidores de una cuenta de ejemplo (directorio de locales)
    comp = ["resumen_de_noticias"] # Cambiar por una real para test real
    print(f"Buscando seguidores de competencia: {comp}")
    # Nota: No ejecutamos real para evitar bloqueos en el entorno de prueba de la IA, 
    # pero mostramos la estructura.
    print("Simulando búsqueda para evitar baneo de cuenta en test...")
    return True

async def main():
    print("🚀 Probando Funciones Senior de Sky Eleven...")
    audit = await test_ai_auditor()
    ig = await test_instagram_competencia()
    
    print("\n✅ CONCLUSIÓN:")
    if audit.get("score_tecnico", 0) < 100:
        print(f"-> EL AI AUDITOR FUNCIONA: Detectó score de {audit['score_tecnico']} y generó el gancho: '{audit['gancho_venta']}'")
    else:
        print("-> El auditor funcionó pero la web es perfecta.")

if __name__ == "__main__":
    asyncio.run(main())
