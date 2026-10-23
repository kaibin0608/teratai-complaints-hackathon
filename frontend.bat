@echo off
rem Double-click to start the frontend on port 5173. Close this window (or press Ctrl+C) to stop it.
rem Start the backend first (backend.bat): the frontend forwards /api to it on port 8000.

cd /d "%~dp0frontend"

where npm >nul 2>nul
if errorlevel 1 (
    echo Node.js is not installed. Install it from https://nodejs.org, then try again.
    pause
    exit /b 1
)

if not exist "node_modules" (
    echo First run: installing packages...
    call npm install --no-audit --no-fund
    if errorlevel 1 (
        echo npm install failed. The error is above.
        pause
        exit /b 1
    )
)

echo Starting the Teratai frontend...
echo   This laptop:     http://localhost:5173
echo   Other laptops:   the "Network:" address below (same Wi-Fi; allow port 5173 in the firewall)
echo   Sign in:         officer1, officer2, fraud1 or manager1 / teratai123
echo.

rem --host so other laptops on the same Wi-Fi can open it.
call npm run dev -- --host

echo.
echo The frontend stopped. If it failed to start, the error is above (port 5173 already in use?).
pause
