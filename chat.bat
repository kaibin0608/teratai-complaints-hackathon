@echo off
rem Double-click to start the case assistant (chatbot) on port 8001. Close this window (or press Ctrl+C) to stop it.
rem It reads the main API's database read-only and never changes a case, so the API on port 8000 keeps running
rem untouched. Start backend.bat first; the frontend forwards /api/chat here.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo No .venv found. Set it up once with:
    echo     python -m venv .venv
    echo     .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting the Teratai case assistant...
echo   Assistant: http://127.0.0.1:8001/api/chat  (health: /api/chat/health)
echo   Uses the reply model from .env (LLM_DRAFT); with fake models it answers from code only.
echo.

".venv\Scripts\python.exe" -m uvicorn backend.chat.app:app --host 0.0.0.0 --port 8001

echo.
echo The assistant stopped. If it failed to start, the error is above (port 8001 already in use?).
pause
