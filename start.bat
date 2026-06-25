@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo   MAHDI Assessment - Local Server
echo ============================================================
echo.

if not exist "backend\data" mkdir "backend\data"

python -m pip show fastapi >nul 2>&1
if errorlevel 1 (
  echo [1/2] Installing backend dependencies...
  python -m pip install -r requirements.txt
)

echo [2/2] Starting local server...
echo.
echo   Open: http://localhost:8010
echo   Teacher: teacher / meitai123456
echo   Data: backend\data\mahid.db
echo.
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8010 --reload

pause
endlocal
