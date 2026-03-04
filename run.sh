#!/bin/bash

echo "------------------------------------------"
echo " UART Hardware Automation - Secure Boot"
echo "------------------------------------------"

# Ensure venv is active (optional, remove if not using venv)
# source venv/bin/activate

export PYTHONPATH=$PYTHONPATH:$(pwd)
mkdir -p logs

echo "[1/3] Running Regression Suite + Coverage Report..."
# Generates a coverage report in the terminal
pytest --cov=app tests/ --cov-report=term-missing

echo "[2/3] Checking Port Permissions..."
if groups | grep -q "\bdialout\b"; then
    echo " Permissions: OK"
else
    echo " Warning: User not in 'dialout' group. Hardware access may fail."
fi

echo "[3/3] Launching Dashboard..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
