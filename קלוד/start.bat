@echo off
echo Starting Knowledge Hub...

:: Check if .env exists
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo Please edit .env and add your API keys, then run this script again.
    pause
    exit /b
)

:: Check if venv exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate venv and install dependencies
call venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt --quiet

:: Start the server
echo.
echo ========================================
echo   Knowledge Hub is starting...
echo   Open http://localhost:8000 in browser
echo ========================================
echo.
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
