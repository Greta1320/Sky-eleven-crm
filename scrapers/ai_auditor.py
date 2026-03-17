import json
import os
import asyncio
from openai import OpenAI # Assuming OpenAI-compatible API or similar is used in this environment

# Config
LEADS_FILE = os.path.join(os.path.dirname(__file__), "outputs", "leads.json")
AUDITED_FILE = os.path.join(os.path.dirname(__file__), "outputs", "leads_audited.json")

# This is a placeholder for the actual AI logic. 
# In a real scenario, this would call an LLM API.
async def analyze_lead(lead):
    name = lead.get('nombre', 'Negocio')
    category = lead.get('category', 'Rubro General')
    website = lead.get('website', '')
    
    # Simple heuristic-based "AI" logic for the prototype
    # If the user has a real OpenAI key, we'd use it here.
    
    if not website:
        audit = f"Detectamos que {name} no tiene sitio web oficial. Esto les hace perder clientes frente a competidores en San Luis que sí aparecen en Google con reserva directa."
        pitch = f"Hola! Vi su perfil en Maps y noté que no tienen web vinculada. Les gustaría ver un demo de cómo un asistente de IA puede tomar reservas por ustedes 24/7?"
    else:
        audit = f"{name} tiene presencia web, pero prodría potenciar su conversión con un asistente de IA para atención al cliente automática."
        pitch = f"Hola! Estuve viendo su web {website}. Sabían que pueden automatizar el 80% de las consultas de sus clientes de San Luis con un bot entrenado con su propia info?"

    lead['ai_audit'] = audit
    lead['ai_personalized_pitch'] = pitch
    return lead

async def main():
    if not os.path.exists(LEADS_FILE):
        print("No se encontró leads.json")
        return

    with open(LEADS_FILE, "r", encoding="utf-8") as f:
        leads = json.load(f)

    print(f"Analizando {len(leads)} leads con IA...")
    
    tasks = [analyze_lead(lead) for lead in leads]
    audited_leads = await asyncio.gather(*tasks)

    with open(AUDITED_FILE, "w", encoding="utf-8") as f:
        json.dump(audited_leads, f, ensure_ascii=False, indent=2)
    
    # Also update the main leads.json to reflect audited status if needed
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(audited_leads, f, ensure_ascii=False, indent=2)

    print(f"✅ Auditoría completada. Resultados en {AUDITED_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
