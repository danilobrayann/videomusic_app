@echo off
chcp 65001 >nul
title VideoMusic Studio - Gerador de Executavel (.EXE)
echo ========================================================
echo        VIDEOMUSIC STUDIO - CRIADOR DE .EXE
echo ========================================================
echo.
echo [1/4] Verificando PyInstaller e dependencias...
pip install -r requirements.txt

echo.
echo [2/4] Gerando icone se necessario...
python create_icon.py

echo.
echo [3/4] Compilando executavel com PyInstaller (Isso pode levar alguns segundos)...
pyinstaller --noconsole --onefile --icon=app_icon.ico --name="VideoMusicStudio" --collect-all customtkinter --add-data="themes;themes" --add-data="app_icon.ico;." --add-data="iptv_channels.json;." app.py

echo.
echo [4/4] Atualizando atalhos do Windows para apontar para o novo .EXE...
python setup_shortcut.py

echo.
echo ========================================================
echo Executavel gerado na pasta: dist\VideoMusicStudio.exe
echo Atalho da Area de Trabalho atualizado para o .EXE!
echo ========================================================
echo.
pause
