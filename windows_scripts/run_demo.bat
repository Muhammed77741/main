@echo off
REM Stock Screener - Demo Version (Fast, No Internet Required)

echo ========================================
echo   Stock Screener - DEMO
echo ========================================
echo.
echo Running demo screener...
echo (Uses simulated data, no internet required)
echo.

cd /d "%~dp0"
cd ..
if exist main\stock_smc_trading (
    cd main\stock_smc_trading
)

REM Activate venv if exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM Run demo screener
python demo_screener.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Screener failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Results saved!
echo ========================================
echo.
echo File: demo_top_stocks.csv
echo Location: %CD%
echo.

REM Ask to open results
set /p OPEN="Open results in Excel? (y/n): "
if /i "%OPEN%"=="y" (
    start excel demo_top_stocks.csv
)

pause
