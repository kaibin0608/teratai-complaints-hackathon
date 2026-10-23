@echo off
rem Double-click to start the backend API on port 8000. Close this window (or press Ctrl+C) to stop it.
rem Models and keys come from .env; with no .env it uses the free offline fake models.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No .venv found. Set it up once with:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting the Teratai complaints backend...
echo   API:       http://127.0.0.1:8000
echo   Try it:    http://127.0.0.1:8000/docs
echo   Check it:  .venv\Scripts\python scoring\api_check.py http://127.0.0.1:8000
echo.

rem 0.0.0.0 so other laptops on the same Wi-Fi (the UI, the organisers) can reach it.
".venv\Scripts\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000

echo.
echo The backend stopped. If it failed to start, the error is above (port 8000 already in use? a missing key in .env?).
pause
