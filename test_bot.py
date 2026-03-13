"""
TEST RÁPIDO — SKY Eleven Bot
=============================
Probá el bot sin necesitar Evolution API ni servidor.
Simplemente corré: python test_bot.py

Esto simula exactamente lo que hace el bot cuando alguien te escribe por WhatsApp.
"""

import sys, types, os

# ── Mock de config para que funcione sin .env ─────────────────────────────────
class Config:
    DB_PATH = 'test_sky_eleven.db'   # Base de datos de prueba local
    EVOLUTION_API_URL = 'http://localhost:8080'
    EVOLUTION_API_KEY = 'test'
    EVOLUTION_INSTANCE = 'sky_eleven'
    WSP_NUMERO_DESTINO = '541100000000'
    WSP_NUMERO_CLIENTE = False
    SCORE_MINIMO_WSP = 70
    DIAS_SEGUIMIENTO = 3

m = types.ModuleType('config')
m.Config = Config
sys.modules['config'] = m

from conversation import ConversationManager

# ── Colores para la terminal ──────────────────────────────────────────────────
CYAN  = '\033[96m'
GREEN = '\033[92m'
AMBER = '\033[93m'
GREY  = '\033[90m'
BOLD  = '\033[1m'
RESET = '\033[0m'

def limpiar():
    if os.path.exists('test_sky_eleven.db'):
        os.remove('test_sky_eleven.db')

def chat_interactivo():
    """Modo interactivo — hablás con el bot como si fuera WhatsApp"""
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  🤖 SKY Eleven Bot — Modo prueba interactivo{RESET}")
    print(f"{'─'*55}")
    print(f"{GREY}  Simulás ser un prospecto que recibe tus mensajes.{RESET}")
    print(f"{GREY}  Escribí 'salir' para terminar, 'nuevo' para nuevo lead.{RESET}")
    print(f"{'─'*55}\n")

    mgr = ConversationManager(Config.DB_PATH)

    print(f"{AMBER}Datos del prospecto de prueba:{RESET}")
    nombre  = input("  Nombre del contacto [Carlos]: ").strip() or "Carlos"
    negocio = input("  Nombre del negocio [Restaurante El Sol]: ").strip() or "Restaurante El Sol"
    ciudad  = input("  Ciudad [CABA]: ").strip() or "CABA"
    tel     = "5491112345678"

    mgr.inicializar_conversacion(tel, nombre, negocio, 1)

    print(f"\n{GREEN}✅ Bot activado para {nombre} / {negocio}{RESET}")
    print(f"{GREY}─── El bot responderá como si fuera por WhatsApp ───{RESET}\n")

    while True:
        try:
            msg = input(f"{CYAN}👤 Vos (como el prospecto): {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nChau!")
            break

        if not msg:
            continue
        if msg.lower() == 'salir':
            break
        if msg.lower() == 'nuevo':
            limpiar()
            chat_interactivo()
            return
        if msg.lower() == 'estado':
            conv = mgr._obtener_conversacion(tel)
            print(f"{GREY}  Estado: {conv['estado']} | Reunión: {conv.get('dia_reunion','-')} {conv.get('hora_reunion','-')}{RESET}\n")
            continue

        respuesta = mgr.procesar(tel, msg)
        conv = mgr._obtener_conversacion(tel)

        print(f"{GREEN}🤖 Bot: {RESET}{respuesta}")
        print(f"{GREY}   [{conv['estado']}]{RESET}\n")

        if conv['estado'] == 'agendado':
            print(f"{GREEN}{BOLD}  🎉 ¡REUNIÓN CONFIRMADA!{RESET}")
            print(f"{GREEN}  📅 {conv['dia_reunion']} a las {conv['hora_reunion']}{RESET}")
            print(f"{GREY}  → En producción, acá te llega WhatsApp con los datos.{RESET}\n")

        if conv['estado'] == 'no_interesado':
            print(f"{AMBER}  Bot cerró la conversación amablemente.{RESET}\n")
            print(f"{GREY}  → En producción, el lead queda como 'No interesado' en el CRM.{RESET}\n")

    limpiar()

def test_automatico():
    """Corre 5 casos automáticos y muestra resultados"""
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}  🧪 Tests automáticos — 5 casos reales{RESET}")
    print(f"{'─'*55}\n")

    casos = [
        ("Restaurante — flujo normal",     "Carlos",  "El Mirador",    ["Sí me interesa", "El miércoles a las 11", "No tenemos web", "Más clientes de la zona"]),
        ("Clínica — pregunta precio",      "Ana",     "DentalPro",     ["¿cuánto cobran?", "el viernes 16hs", "web del 2017", "más pacientes"]),
        ("Abogado — no tiene tiempo",      "Jorge",   "Estudio Mora",  ["me interesa", "ahora no puedo", "lunes 10hs", "sin web", "clientes corporativos"]),
        ("Spa — dice no le interesa",      "Laura",   "Spa Serenidad", ["no me interesa, gracias"]),
        ("Academia — va directo al grano", "Liz",     "Spark English", ["dale sí", "jueves 15hs", "solo WhatsApp", "alumnos online"]),
    ]

    resultados = []
    for titulo, nombre, negocio, msgs in casos:
        mgr = ConversationManager(':memory:')
        tel = f"549111{len(resultados)}111111"
        mgr.inicializar_conversacion(tel, nombre, negocio, len(resultados)+1)

        print(f"{BOLD}📍 {titulo}{RESET}")
        for msg in msgs:
            r = mgr.procesar(tel, msg)
            conv = mgr._obtener_conversacion(tel)
            print(f"  {CYAN}👤{RESET} {msg}")
            print(f"  {GREEN}🤖{RESET} {r[:75]}{'...' if len(r)>75 else ''}")
            print(f"     {GREY}[{conv['estado']}]{RESET}")

        conv = mgr._obtener_conversacion(tel)
        estado = conv['estado']
        ok = estado == 'agendado' or (titulo.startswith('Spa') and estado == 'no_interesado')
        resultados.append(ok)

        if ok:
            reunion = f"{conv.get('dia_reunion','')} {conv.get('hora_reunion','')}".strip()
            print(f"  {GREEN}✅ OK — {estado} {reunion}{RESET}\n")
        else:
            print(f"  {AMBER}⚠️  Estado inesperado: {estado}{RESET}\n")

    pasaron = sum(resultados)
    print(f"{'─'*55}")
    print(f"{BOLD}RESULTADO: {pasaron}/{len(resultados)} tests pasaron{RESET}")
    if pasaron == len(resultados):
        print(f"{GREEN}✅ Bot listo para producción{RESET}\n")
    else:
        print(f"{AMBER}⚠️  Revisar casos fallidos{RESET}\n")

# ── MENÚ ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"\n{BOLD}SKY Eleven — Tester{RESET}")
    print("¿Qué querés probar?")
    print("  1. Chat interactivo (hablás vos con el bot)")
    print("  2. Tests automáticos (5 casos de una)")
    print("  3. Ambos")

    op = input("\nOpción [1]: ").strip() or "1"

    if op == "1":
        chat_interactivo()
    elif op == "2":
        test_automatico()
    elif op == "3":
        test_automatico()
        chat_interactivo()
    else:
        chat_interactivo()
