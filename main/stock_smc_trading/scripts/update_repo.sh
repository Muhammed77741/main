#!/bin/bash
#
# Repository Update Script
# Pulls latest changes and reinstalls dependencies if needed
#

REPO_DIR="$HOME/main"
SCREENER_DIR="$REPO_DIR/main/stock_smc_trading"
LOG_FILE="$HOME/screener_logs/update_$(date +%Y%m%d_%H%M%S).log"

mkdir -p ~/screener_logs

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

log "=========================================="
log "Repository Update Started"
log "=========================================="

# Go to repo
cd $REPO_DIR || {
    log "ERROR: Cannot cd to $REPO_DIR"
    exit 1
}

# Save current commit
CURRENT_COMMIT=$(git rev-parse HEAD)
log "Current commit: $CURRENT_COMMIT"

# Fetch and pull
log "Fetching from origin..."
git fetch origin >> $LOG_FILE 2>&1

log "Pulling changes..."
git pull origin claude/simplify-stock-screener-WzlXB >> $LOG_FILE 2>&1

# Check if updated
NEW_COMMIT=$(git rev-parse HEAD)
log "New commit: $NEW_COMMIT"

if [ "$CURRENT_COMMIT" == "$NEW_COMMIT" ]; then
    log "Already up to date"
else
    log "Repository updated!"

    # Check if requirements.txt changed
    if git diff --name-only $CURRENT_COMMIT $NEW_COMMIT | grep -q requirements.txt; then
        log "requirements.txt changed, updating dependencies..."

        cd $SCREENER_DIR
        if [ -d "venv" ]; then
            source venv/bin/activate
            pip install -r requirements.txt -q
            log "Dependencies updated"
        fi
    fi
fi

log "=========================================="
log "Update Completed"
log "=========================================="
