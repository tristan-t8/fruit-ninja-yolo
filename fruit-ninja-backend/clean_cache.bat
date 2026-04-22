@echo off
REM Clean Python cache files
cd /d "%~dp0"

echo Cleaning Python cache...

if exist "__pycache__" (
    rmdir /s /q __pycache__
    echo Deleted __pycache__
)

if exist "venv\__pycache__" (
    rmdir /s /q venv\__pycache__
    echo Deleted venv\__pycache__
)

for /d %%i in (*.pyc) do del /q "%%i" 2>nul

echo.
echo Cache cleaned. You can now run start_server.bat
echo.
pause
