@echo off
title Rastreador Uber 3.0 - Delta Silk Print
cd /d "%~dp0"
python app.py
if %ERRORLEVEL% neq 0 (
    echo.
    echo ════════════════════════════════════════════════════
    echo   ERRO: Certifique-se de ter Python e as dependencias
    echo   pip install customtkinter selenium plyer Pillow
    echo ════════════════════════════════════════════════════
    pause
)
