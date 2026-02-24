@echo off
title UberTrack by Delta
cd /d "%~dp0"

:: Usa o pythonw / pyw para rodar em modo silencioso (sem tela preta do cmd)
start "" pyw app.py 2>nul || start "" pythonw app.py
