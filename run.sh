#!/bin/bash

echo "------------------------------------------"
echo " Starting UART Hardware Automation Tool"
echo "------------------------------------------"

source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)
mkdir -p logs

if groups | grep -q "\bdialout\b"; then
    echo " Permissions: OK"
else
    echo "Adding user to dialout group..."
    sudo usermod -a -G dialout $USER
fi

echo " Running diagnostic tests..."
pytest tests/test_uart.py

echo " Launching Dashboard at http://127.0.0.1:8000"
uvicorn app.main:app --host 0.0.0.0 --port 8000
