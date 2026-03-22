@echo off
title Reparar Dependencias - SKY Eleven
echo Instalando dependencias necesarias...
pip install -r Agente_AI\requirements.txt
echo.
echo Instalando navegador para Google Maps (Playwright)...
python -m playwright install chromium
echo.
echo ¡Todo listo! Ya podés cerrar esta ventana y usar INICIAR_AGENTE.bat
pause
