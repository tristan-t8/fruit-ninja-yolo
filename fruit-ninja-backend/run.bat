@echo off
REM Fruit Ninja YOLO Backend - Windows Startup Script

echo ================================
echo Fruit Ninja YOLO Backend
echo ================================
echo.

REM Check Python
echo [1/5] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python %PYTHON_VERSION% found
echo.

REM Create virtual environment
echo [2/5] Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created
) else (
    echo Virtual environment already exists
)
echo.

REM Activate virtual environment
echo [3/5] Activating virtual environment...
call venv\Scripts\activate.bat
echo Virtual environment activated
echo.

REM Upgrade pip
echo [4/5] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel >nul 2>&1
echo Pip upgraded
echo.

REM Install requirements
echo [5/5] Installing dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo Dependencies installed
) else (
    echo Error: requirements.txt not found
    pause
    exit /b 1
)
echo.

REM Check CUDA
echo Checking CUDA availability...
python -c "import torch; print('CUDA Available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
echo.

REM Create logs directory
if not exist "logs" (
    mkdir logs
)

echo ================================
echo Ready to start server!
echo ================================
echo.

echo Starting Fruit Ninja YOLO Backend Server...
echo.

REM Run the application
python app.py

pause
