@echo off
REM ============================================================
REM Fruit Ninja YOLO Backend - START SERVER
REM ============================================================

REM Change to the directory where this batch file is located
cd /d "%~dp0"

echo.
echo ============================================================
echo  Fruit Ninja YOLO Backend - Starting Server
echo ============================================================
echo.
echo Working directory: %CD%
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found or broken!
    echo.
    echo Expected: %CD%\venv\Scripts\activate.bat
    echo.
    echo Please run setup.bat first.
    echo If you already ran it, setup may have failed.
    echo Try running setup.bat again.
    echo.
    pause
    exit /b 1
)

REM Check if app.py exists
if not exist "app.py" (
    echo ERROR: app.py not found in %CD%
    echo.
    echo Make sure this batch file is in the same folder as app.py
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

REM Verify dependencies are installed
python -c "import torch, flask, ultralytics" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Required packages are not installed.
    echo Please run setup.bat first.
    echo.
    pause
    exit /b 1
)

REM Create logs folder if missing
if not exist "logs" mkdir logs

echo.
echo ============================================================
echo  Server URLs:
echo    Main:        http://localhost:5000
echo    Test Page:   http://localhost:5000/test
echo    Health:      http://localhost:5000/health
echo ============================================================
echo.
echo Press CTRL+C to stop the server
echo.

REM Start the server
python app.py

REM If python exits with error, pause so user can see what happened
if errorlevel 1 (
    echo.
    echo Server stopped with an error.
    pause
)
