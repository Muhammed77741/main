@echo off
echo ========================================
echo   Stock Screener - FIXED VERSION
echo   (Works with Russian characters in path)
echo ========================================
echo.

cd /d "%~dp0\..\main\stock_smc_trading"

REM Activate venv if exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo Running SSL-fixed screener...
echo.

python real_data_screener_fixed.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo   SUCCESS!
    echo ========================================
    echo.
    echo Results: real_data_screener_results.csv
    echo.

    REM Ask to open in Excel
    set /p OPEN="Open results in Excel? (y/n): "
    if /i "%OPEN%"=="y" (
        start excel real_data_screener_results.csv
    )
) else (
    echo.
    echo ========================================
    echo   ERROR - Trying demo version...
    echo ========================================
    echo.
    python demo_screener.py

    if %ERRORLEVEL% EQU 0 (
        echo.
        echo Demo version worked!
        echo Results: demo_top_stocks.csv
        start excel demo_top_stocks.csv
    )
)

echo.
pause
