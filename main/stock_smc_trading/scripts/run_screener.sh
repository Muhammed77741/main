#!/bin/bash
#
# Stock Screener Runner Script
# Automatically runs the screener and saves results with logs
#

# Configuration
REPO_DIR="$HOME/main/main/stock_smc_trading"
VENV_DIR="$REPO_DIR/venv"
LOG_DIR="$HOME/screener_logs"
RESULTS_DIR="$HOME/screener_results"

# Create directories if they don't exist
mkdir -p $LOG_DIR
mkdir -p $RESULTS_DIR

# Date for filename
DATE=$(date +%Y%m%d_%H%M%S)
DATE_SHORT=$(date +%Y%m%d)

# Log file
LOG_FILE="$LOG_DIR/screener_${DATE}.log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=========================================="
log "Stock Screener Started"
log "=========================================="

# Change to repo directory
cd $REPO_DIR || {
    log "ERROR: Cannot cd to $REPO_DIR"
    exit 1
}

log "Working directory: $(pwd)"

# Activate virtual environment if exists
if [ -d "$VENV_DIR" ]; then
    log "Activating virtual environment..."
    source $VENV_DIR/bin/activate
else
    log "WARNING: No virtual environment found at $VENV_DIR"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version)
log "Python version: $PYTHON_VERSION"

# Run the screener
log "Running real_data_screener.py..."
python3 real_data_screener.py >> $LOG_FILE 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    log "ERROR: Screener exited with code $EXIT_CODE"
    exit $EXIT_CODE
fi

log "Screener completed successfully"

# Copy results with timestamp
if [ -f "real_data_screener_results.csv" ]; then
    cp real_data_screener_results.csv "$RESULTS_DIR/results_${DATE}.csv"
    cp real_data_screener_results.csv "$RESULTS_DIR/latest.csv"
    log "Results saved to:"
    log "  - $RESULTS_DIR/results_${DATE}.csv"
    log "  - $RESULTS_DIR/latest.csv"

    # Show row count
    ROW_COUNT=$(wc -l < real_data_screener_results.csv)
    log "Total rows in results: $ROW_COUNT"
else
    log "WARNING: No results file found"
fi

# Cleanup old logs (keep last 7 days)
log "Cleaning up old logs..."
find $LOG_DIR -name "screener_*.log" -mtime +7 -delete
find $RESULTS_DIR -name "results_*.csv" -mtime +7 -delete
log "Old logs cleaned (kept last 7 days)"

log "=========================================="
log "Stock Screener Finished"
log "=========================================="
