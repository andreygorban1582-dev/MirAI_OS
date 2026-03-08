@echo off
:: ─── MirAI_OS  –  Start (Windows / WSL2) ────────────────────────────────────
title MirAI_OS
color 0A
echo Starting MirAI_OS stack in WSL2...
wsl -d kali-linux -- bash -c "cd '%~dp0' && docker compose up -d && echo MirAI_OS started."
echo.
echo  Web UI  :  https://localhost
echo  API     :  http://localhost:8080
echo  N8n     :  http://localhost:5678
echo  Kali VNC:  http://localhost:6901
echo.
pause
