@echo off
rem Query2Diagnose: starts the website and live demo on http://localhost:8000
rem and restarts the server automatically if it ever stops. Close this window to quit.
cd /d "%~dp0"
title Query2Diagnose server
start "" cmd /c "timeout /t 8 /nobreak >/dev/null & start http://localhost:8000"
:run
echo Starting the server (the model loads in the background; the page works at once)...
.venv\Scripts\python -I -m uvicorn api.main:app --host 127.0.0.1 --port 8000
echo.
echo The server stopped. Restarting in 3 seconds... (close this window to quit)
timeout /t 3 /nobreak >nul
goto run
