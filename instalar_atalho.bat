@echo off
chcp 65001 >nul
title VideoMusic Studio - Instalador de Dependências e Atalho
echo ========================================================
echo        VIDEOMUSIC STUDIO - INSTALADOR DE ATALHO
echo ========================================================
echo.
echo [1/3] Verificando e instalando dependencias (customtkinter, pillow, pygame, yt-dlp)...
pip install -r requirements.txt

echo.
echo [2/3] Gerando icone da aplicacao...
python create_icon.py

echo.
echo [3/3] Criando atalho na Area de Trabalho e Menu Iniciar...
python setup_shortcut.py

echo.
echo ========================================================
echo Instalacao concluida com sucesso!
echo Voce ja pode abrir o app pelo atalho na Area de Trabalho.
echo ========================================================
echo.
pause
