@echo off
title Servidor Prospectador 3.0
cd Agente_AI
echo Iniciando servidor en puerto 3000...
python -m uvicorn server:app --host 0.0.0.0 --port 3000
pause
