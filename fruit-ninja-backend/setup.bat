@echo off
REM ============================================================
REM Fruit Ninja YOLO Backend - FIRST TIME SETUP
REM Run this ONCE to install everything
REM ============================================================

REM Change to the directory where this batch file is located
cd /d "%~dp0"

echo.
echo ============================================================
echo  Fruit Ninja YOLO Backend - First Time Setup
echo ============================================================
echo.
echo Working directory: %CD%
echo.

REM Step 1: Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed or not in PATH!
    echo.
    echo Please install Python 3.10 or 3.11 from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)
python --version
echo.

REM Step 2: Remove old broken venv if exists
echo [2/5] Preparing virtual environment...
if exist "venv" (
    echo Found existing venv folder. Checking if it works...
    if not exist "venv\Scripts\activate.bat" (
        echo Broken venv detected. Removing...
        rmdir /s /q venv
        echo Old venv removed.
    ) else (
        echo Existing venv looks valid.
    )
)
echo.

REM Step 3: Create virtual environment
echo [3/5] Creating virtual environment...
if not exist "venv\Scripts\activate.bat" (
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment
        echo.
        echo Possible fixes:
        echo   1. Run this as Administrator
        echo   2. Make sure you are not inside a OneDrive/cloud folder
        echo   3. Try: python -m pip install --upgrade virtualenv
        echo.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
) else (
    echo Virtual environment already exists
)

REM Verify venv was actually created
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo ERROR: venv was not created properly!
    echo Expected file: venv\Scripts\activate.bat
    echo.
    pause
    exit /b 1
)
echo.

REM Step 4: Activate and upgrade pip
echo [4/5] Activating environment and upgrading pip...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
python -m pip install --upgrade pip setuptools wheel
echo.

REM Step 5: Install dependencies
echo [5/5] Installing dependencies (this will take several minutes)...
echo.
echo Do you have an NVIDIA GPU and want GPU acceleration?
echo   Y = Install with CUDA 11.8 GPU support (faster, requires NVIDIA GPU)
echo   N = Install CPU-only version (works on any computer)
echo.
set /p GPU_CHOICE="Install GPU version? (Y/N): "

if /i "%GPU_CHOICE%"=="Y" (
    echo.
    echo Installing PyTorch with CUDA 11.8...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
) else (
    echo.
    echo Installing CPU-only PyTorch...
    pip install torch torchvision
)

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install PyTorch
    pause
    exit /b 1
)

echo.
echo Installing other dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Create logs folder
if not exist "logs" mkdir logs

echo.
echo ============================================================
echo  SETUP COMPLETE!
echo ============================================================
echo.
echo Checking your setup...
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
echo.
echo To start the server, double-click: start_server.bat
echo.
pause
