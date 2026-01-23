#!/bin/bash
#
# Stock Screener - One-Click Installer
# Полностью автоматическая установка на Ubuntu/Debian
#
# Usage: bash install.sh
#

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Icons
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
INFO="${BLUE}ℹ${NC}"
WARN="${YELLOW}⚠${NC}"

# Script start
clear
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║                                                       ║"
echo "║         STOCK SCREENER AUTO-INSTALLER                ║"
echo "║                                                       ║"
echo "║         Automatic setup for Ubuntu/Debian            ║"
echo "║                                                       ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}\n"

# Log function
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    log_error "This script requires Linux (Ubuntu/Debian)"
    exit 1
fi

log_info "Detected OS: $(lsb_release -d | cut -f2)"
log_info "Installation will take ~5 minutes"
echo ""

# Step 1: Update system
log "Step 1/8: Updating system packages..."
if command -v apt &> /dev/null; then
    sudo apt update -qq > /dev/null 2>&1
    log "$CHECK System packages updated"
else
    log_error "apt not found. This script requires Ubuntu/Debian"
    exit 1
fi

# Step 2: Install system dependencies
log "Step 2/8: Installing system dependencies..."
sudo apt install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    build-essential \
    python3-dev \
    > /dev/null 2>&1

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
log "$CHECK Python $PYTHON_VERSION installed"
log "$CHECK Git installed"
log "$CHECK Build tools installed"

# Step 3: Clone repository (if not already)
REPO_DIR="$HOME/main"
SCREENER_DIR="$REPO_DIR/main/stock_smc_trading"

log "Step 3/8: Setting up repository..."
if [ -d "$REPO_DIR" ]; then
    log_info "Repository already exists, pulling latest changes..."
    cd $REPO_DIR
    git pull origin claude/simplify-stock-screener-WzlXB > /dev/null 2>&1
else
    log_info "Cloning repository from GitHub..."
    cd $HOME
    git clone -q https://github.com/Muhammed77741/main.git > /dev/null 2>&1
fi
log "$CHECK Repository ready at $REPO_DIR"

# Step 4: Create virtual environment
log "Step 4/8: Creating Python virtual environment..."
cd $SCREENER_DIR

if [ -d "venv" ]; then
    log_info "Virtual environment already exists"
else
    python3 -m venv venv > /dev/null 2>&1
    log "$CHECK Virtual environment created"
fi

# Step 5: Install Python dependencies
log "Step 5/8: Installing Python packages..."
source venv/bin/activate

# Upgrade pip quietly
pip install --upgrade pip -q > /dev/null 2>&1

# Install requirements
pip install -q pandas numpy > /dev/null 2>&1
log "$CHECK pandas and numpy installed"

# Try to install yfinance (may fail, that's ok)
if pip install -q yfinance > /dev/null 2>&1; then
    log "$CHECK yfinance installed (real data available)"
else
    log_warn "yfinance failed to install (will use demo data)"
fi

# Step 6: Create directories
log "Step 6/8: Creating log and results directories..."
mkdir -p $HOME/screener_logs
mkdir -p $HOME/screener_results
log "$CHECK Directories created"
log "   - Logs: $HOME/screener_logs"
log "   - Results: $HOME/screener_results"

# Step 7: Make scripts executable
log "Step 7/8: Setting up execution scripts..."
chmod +x scripts/*.sh 2>/dev/null || true
log "$CHECK Scripts are executable"

# Step 8: Test installation
log "Step 8/8: Testing installation..."
log_info "Running quick test..."

if python3 demo_screener.py > /dev/null 2>&1; then
    log "$CHECK Demo screener works!"
else
    log_warn "Demo screener test failed (not critical)"
fi

# Deactivate venv
deactivate

# Setup cron (ask user)
echo ""
echo -e "${YELLOW}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║                                                       ║${NC}"
echo -e "${YELLOW}║              SETUP AUTOMATIC SCHEDULING?              ║${NC}"
echo -e "${YELLOW}║                                                       ║${NC}"
echo -e "${YELLOW}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Do you want to setup automatic daily runs? ${GREEN}(recommended)${NC}"
echo -e "The screener will run every day at 9:00 AM UTC"
echo ""
read -p "Setup cron? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "Setting up cron job..."

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "run_screener.sh"; then
        log_info "Cron job already exists"
    else
        # Add cron job
        (crontab -l 2>/dev/null; echo "0 9 * * * $SCREENER_DIR/scripts/run_screener.sh") | crontab -
        log "$CHECK Cron job added (runs daily at 9:00 AM UTC)"
    fi

    # Show cron schedule
    echo ""
    log_info "Current schedule:"
    echo -e "${BLUE}$(crontab -l | grep run_screener.sh)${NC}"
fi

# Installation complete
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                       ║${NC}"
echo -e "${GREEN}║            🎉 INSTALLATION COMPLETE! 🎉               ║${NC}"
echo -e "${GREEN}║                                                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

# Show summary
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    SUMMARY                            ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📁 Installation directory: ${GREEN}$SCREENER_DIR${NC}"
echo -e "🐍 Python version: ${GREEN}$PYTHON_VERSION${NC}"
echo -e "📊 Virtual environment: ${GREEN}$SCREENER_DIR/venv${NC}"
echo -e "📝 Logs: ${GREEN}$HOME/screener_logs${NC}"
echo -e "💾 Results: ${GREEN}$HOME/screener_results${NC}"
echo ""

# Show next steps
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                   NEXT STEPS                          ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}1. Test manual run:${NC}"
echo -e "   cd $SCREENER_DIR"
echo -e "   ./scripts/run_screener.sh"
echo ""
echo -e "${GREEN}2. View results:${NC}"
echo -e "   cat ~/screener_results/latest.csv"
echo ""
echo -e "${GREEN}3. Check logs:${NC}"
echo -e "   tail -f ~/screener_logs/screener_*.log"
echo ""
echo -e "${GREEN}4. Change schedule (optional):${NC}"
echo -e "   crontab -e"
echo ""
echo -e "${GREEN}5. Update code:${NC}"
echo -e "   cd $SCREENER_DIR"
echo -e "   ./scripts/update_repo.sh"
echo ""

# Show available commands
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                 QUICK COMMANDS                        ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}# Run screener manually:${NC}"
echo -e "cd $SCREENER_DIR && ./scripts/run_screener.sh"
echo ""
echo -e "${YELLOW}# Run demo version (fast, no internet):${NC}"
echo -e "cd $SCREENER_DIR && source venv/bin/activate && python3 demo_screener.py"
echo ""
echo -e "${YELLOW}# Run with real data (requires internet):${NC}"
echo -e "cd $SCREENER_DIR && source venv/bin/activate && python3 real_data_screener.py"
echo ""
echo -e "${YELLOW}# View latest results:${NC}"
echo -e "cat ~/screener_results/latest.csv"
echo ""
echo -e "${YELLOW}# View all results:${NC}"
echo -e "ls -lh ~/screener_results/"
echo ""
echo -e "${YELLOW}# Check logs:${NC}"
echo -e "ls ~/screener_logs/"
echo ""

# Show cron info if enabled
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}              AUTOMATIC SCHEDULING                     ${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}✓${NC} Screener will run automatically every day at 9:00 AM UTC"
    echo -e "${GREEN}✓${NC} Results will be saved to: ~/screener_results/"
    echo -e "${GREEN}✓${NC} Logs will be saved to: ~/screener_logs/"
    echo ""
    echo -e "To change schedule: ${YELLOW}crontab -e${NC}"
    echo -e "To view schedule: ${YELLOW}crontab -l${NC}"
    echo ""
fi

# Final notes
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                      NOTES                            ${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "📚 Documentation:"
echo -e "   - Full guide: $SCREENER_DIR/VPS_DEPLOYMENT.md"
echo -e "   - Quick start: $SCREENER_DIR/QUICKSTART_VPS.md"
echo -e "   - Data sources: $SCREENER_DIR/DATA_SOURCES.md"
echo -e "   - Free hosting: $SCREENER_DIR/FREE_HOSTING.md"
echo ""
echo -e "💡 Tips:"
echo -e "   - Use ${YELLOW}htop${NC} to monitor resources: ${YELLOW}sudo apt install htop${NC}"
echo -e "   - Use ${YELLOW}tmux${NC} for persistent sessions: ${YELLOW}sudo apt install tmux${NC}"
echo -e "   - Check disk usage: ${YELLOW}df -h${NC}"
echo ""
echo -e "${GREEN}Happy screening! 🚀${NC}"
echo ""
