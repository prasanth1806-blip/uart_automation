#!/bin/bash
ulimit -n 1048576
echo "------------------------------------------"
echo " UART AUTOMATION - SYSTEM PRE-FLIGHT"
echo "------------------------------------------"

if [ -d "venv" ]; then
    echo "[0/4] Activating Virtual Environment..."
    source venv/bin/activate
    trap deactivate EXIT
else
    echo "[!] Warning: venv folder not found. Running with system python."
fi

# 1. Fix Permissions
echo "[1/4] Checking USB Permissions..."
sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB* 2>/dev/null || echo "No USB devices found yet."

# 2. Fix Linux System Conflicts
echo "[2/4] Disabling common UART blockers (brltty)..."
sudo systemctl stop brltty-udev.service 2>/dev/null
sudo systemctl mask brltty-udev.service 2>/dev/null

# 3. Run pytest in isolated temp directory so test writes to a throwaway
#    history.jsonl — never the production logs/ folder.
#    This stops test_simulator_execution() from polluting history.jsonl
#    with SIMULATOR_PORT entries before uvicorn starts.
echo "[3/4] Running Reliability Suite (Pytest-Cov)..."
export PYTHONPATH=$PYTHONPATH:$(pwd)
mkdir -p logs

# Point UARTManager base_dir at a temp folder during tests only
export UART_TEST_MODE=1
TMPDIR=$(mktemp -d)
export UART_LOG_DIR="$TMPDIR"
python3 -m pytest --cov=app tests/ --cov-report=term-missing
rm -rf "$TMPDIR"
unset UART_TEST_MODE
unset UART_LOG_DIR

# 4. Launch Dashboard
echo "[4/4] Launching Dashboard on http://localhost:8000"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
