#!/bin/bash
#
# VPS Setup Script
# Automated installation and configuration of Stock Screener
#

set -e  # Exit on error

echo "=========================================="
echo "Stock Screener VPS Setup"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    log_error "This script requires Linux"
    exit 1
fi

# Step 1: Update system
log_info "Updating system packages..."
if command -v apt &> /dev/null; then
    sudo apt update -qq
    sudo apt upgrade -y -qq
    log_success "System updated (Debian/Ubuntu)"
elif command -v yum &> /dev/null; then
    sudo yum update -y -q
    log_success "System updated (CentOS/RHEL)"
fi

# Step 2: Install Python
log_info "Installing Python 3 and pip..."
if command -v apt &> /dev/null; then
    sudo apt install -y python3 python3-pip python3-venv git -qq
elif command -v yum &> /dev/null; then
    sudo yum install -y python3 python3-pip git -q
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log_success "Python installed: $PYTHON_VERSION"

# Step 3: Clone repository
REPO_DIR="$HOME/main"
if [ -d "$REPO_DIR" ]; then
    log_info "Repository already exists, pulling latest changes..."
    cd $REPO_DIR
    git pull origin claude/simplify-stock-screener-WzlXB
else
    log_info "Cloning repository..."
    cd ~
    git clone https://github.com/Muhammed77741/main.git
    log_success "Repository cloned"
fi

# Step 4: Create virtual environment
SCREENER_DIR="$REPO_DIR/main/stock_smc_trading"
cd $SCREENER_DIR

if [ ! -d "venv" ]; then
    log_info "Creating virtual environment..."
    python3 -m venv venv
    log_success "Virtual environment created"
fi

# Step 5: Install dependencies
log_info "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

if pip list | grep -q yfinance; then
    log_success "Dependencies installed"
else
    log_error "Failed to install yfinance"
    exit 1
fi

# Step 6: Test run
log_info "Testing screener..."
python3 demo_screener.py > /dev/null 2>&1 && log_success "Demo screener works" || log_error "Demo screener failed"

# Step 7: Create directories
log_info "Creating log directories..."
mkdir -p ~/screener_logs
mkdir -p ~/screener_results
log_success "Directories created"

# Step 8: Make scripts executable
chmod +x scripts/*.sh
log_success "Scripts are executable"

# Step 9: Setup cron (optional)
echo ""
log_info "Would you like to setup automatic daily runs? (y/n)"
read -r SETUP_CRON

if [[ "$SETUP_CRON" =~ ^[Yy]$ ]]; then
    log_info "Setting up cron job..."

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "run_screener.sh"; then
        log_info "Cron job already exists"
    else
        # Add cron job (run daily at 9:00 AM)
        (crontab -l 2>/dev/null; echo "0 9 * * * $SCREENER_DIR/scripts/run_screener.sh") | crontab -
        log_success "Cron job added (runs daily at 9:00 AM)"
    fi
fi

# Step 10: Summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Directory: $SCREENER_DIR"
echo "Virtual env: $SCREENER_DIR/venv"
echo "Logs: ~/screener_logs"
echo "Results: ~/screener_results"
echo ""
echo "Next steps:"
echo "1. Test manual run:"
echo "   cd $SCREENER_DIR"
echo "   ./scripts/run_screener.sh"
echo ""
echo "2. View results:"
echo "   cat ~/screener_results/latest.csv"
echo ""
echo "3. Check logs:"
echo "   tail -f ~/screener_logs/screener_*.log"
echo ""

if [[ "$SETUP_CRON" =~ ^[Yy]$ ]]; then
    echo "4. Cron scheduled (9:00 AM daily)"
    echo "   To change: crontab -e"
else
    echo "4. To setup auto-run:"
    echo "   crontab -e"
    echo "   Add: 0 9 * * * $SCREENER_DIR/scripts/run_screener.sh"
fi

echo ""
log_success "All done! Happy screening!"
