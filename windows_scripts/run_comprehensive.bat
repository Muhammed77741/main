@echo off
REM Stock Screener - Comprehensive Analysis (Technical + Fundamental)

echo ========================================
echo   Stock Screener - COMPREHENSIVE
echo ========================================
echo.
echo Running full analysis...
echo   - Technical analysis (50 points)
echo   - Fundamental analysis (50 points)
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

REM Run comprehensive screener
python comprehensive_screener.py

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
echo File: comprehensive_screener_results.csv
echo Location: %CD%
echo.

REM Auto-open in Excel
if exist comprehensive_screener_results.csv (
    start excel comprehensive_screener_results.csv
)

pause
