# SKY Eleven — Sistema de Prospección Autónomo

## Archivos principales
- `dashboard.html` → Abrí directo en Chrome para usar
- `server.py` → Backend API (FastAPI)
- `bot.py` → Bot WhatsApp (webhook)
- `agent.py` → Agente scraper orquestador
- `test_bot.py` → Probar el bot sin WhatsApp

## Arrancar
```bash
pip install fastapi uvicorn httpx python-dotenv schedule
cp .env.example .env
# Completar .env con tus datos
uvicorn server:app --host 0.0.0.0 --port 3000
```

## Probar sin Evolution API
```bash
python test_bot.py
```
