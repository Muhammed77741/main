@echo off
REM Stock Screener - Installation Script for Windows
REM Installs all dependencies

echo ========================================
echo   Stock Screener - Installation
echo ========================================
echo.
echo This will install all required packages.
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created
echo.

REM Activate venv
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo.
echo Installing dependencies...
echo   - pandas
pip install pandas --quiet
echo   - numpy
pip install numpy --quiet

REM Try to install yfinance
echo   - yfinance (for real data)
pip install yfinance --quiet
if %errorlevel% neq 0 (
    echo   [WARN] yfinance installation failed
    echo   [INFO] Will use demo data instead
) else (
    echo   [OK] yfinance installed
)

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Double-click run_demo.bat to test
echo   2. Or run_real.bat for real data
echo.
pause
