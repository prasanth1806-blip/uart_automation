#!/bin/bash
echo "------------------------------------------"
echo " UART AUTOMATION - SYSTEM PRE-FLIGHT"
echo "------------------------------------------"

# --- NEW: AUTO VENV ACTIVATION ---
if [ -d "venv" ]; then
    echo "[0/4] Activating Virtual Environment..."
    source venv/bin/activate
    # Deactivate venv automatically when the script exits or is killed (Ctrl+C)
    trap deactivate EXIT
else
    echo "[!] Warning: venv folder not found. Running with system python."
fi
# ---------------------------------

# 1. Fix Permissions Automatically
echo "[1/4] Checking USB Permissions..."
sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB* 2>/dev/null || echo "No USB devices found yet."

# 2. Fix Linux System Conflicts (Common for CH340/FTDI)
echo "[2/4] Disabling common UART blockers (brltty)..."
sudo systemctl stop brltty-udev.service 2>/dev/null
sudo systemctl mask brltty-udev.service 2>/dev/null

# 3. Run Coverage Suite
echo "[3/4] Running Reliability Suite (Pytest-Cov)..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
mkdir -p logs
python3 -m pytest --cov=app tests/ --cov-report=term-missing

# 4. Launch Hub
echo "[4/4] Launching Dashboard on http://localhost:8000"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
