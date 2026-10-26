@echo off
REM Doble clic para: actualizar BD -> recalcular -> abrir la web
cd /d "%~dp0"
if exist venv\Scripts\activate.bat  call venv\Scripts\activate.bat
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python iniciar.py %*
pause
