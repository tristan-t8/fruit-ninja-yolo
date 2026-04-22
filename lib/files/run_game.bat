@echo off
REM ============================================================
REM  Run Flutter Fruit Cutting Game with hand detection
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo  Flutter Fruit Cutting Game - with Hand Detection
echo ============================================================
echo.
echo NOTE: Make sure the Python backend is running first!
echo       (run start_server.bat in the backend folder)
echo.

REM Apply Flutter safe.directory fixes
git config --global --add safe.directory E:/code/flutter >nul 2>&1
git config --global --add safe.directory "%CD%" >nul 2>&1

REM Check flutter is available
where flutter >nul 2>&1
if errorlevel 1 (
    echo ERROR: Flutter is not in PATH.
    echo Please make sure Flutter is installed and added to PATH.
    pause
    exit /b 1
)

echo [1/3] Getting Flutter packages...
flutter pub get
if errorlevel 1 (
    echo ERROR: flutter pub get failed.
    pause
    exit /b 1
)

echo.
echo [2/3] Choose target platform:
echo   1 = Windows desktop   (recommended)
echo   2 = Chrome browser    (easiest if Windows desktop fails)
echo.
set /p PLATFORM="Enter 1 or 2: "

echo.
echo [3/3] Choose what to run:
echo   1 = Full game (your modified fruit cutting game)
echo   2 = Hand tracking test (simple test, verify webcam + backend)
echo.
set /p TARGET="Enter 1 or 2: "

set TARGET_FLAG=
if "%TARGET%"=="2" (
    set TARGET_FLAG=-t lib/main_hand_test.dart
    echo Running hand tracking test...
) else (
    echo Running full game...
)

echo.
if "%PLATFORM%"=="2" (
    flutter run -d chrome %TARGET_FLAG%
) else (
    flutter run -d windows %TARGET_FLAG%
)

pause
