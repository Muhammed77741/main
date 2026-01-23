@echo off
REM Stock Screener - Real Data Version (Requires Internet)

echo ========================================
echo   Stock Screener - REAL DATA
echo ========================================
echo.
echo Running screener with real data from Yahoo Finance...
echo This may take 2-3 minutes.
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

REM Run real data screener
python real_data_screener.py

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Screener failed!
    echo.
    echo Trying demo version instead...
    python demo_screener.py
    set RESULT_FILE=demo_top_stocks.csv
) else (
    set RESULT_FILE=real_data_screener_results.csv
)

echo.
echo ========================================
echo   Results saved!
echo ========================================
echo.
echo File: %RESULT_FILE%
echo Location: %CD%
echo.

REM Auto-open in Excel
if exist "%RESULT_FILE%" (
    echo Opening results in Excel...
    start excel "%RESULT_FILE%"
)

pause
