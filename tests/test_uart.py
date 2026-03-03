import pytest
from app.uart_manager import UARTManager

def test_flexible_port_logic():
    manager = UARTManager()
    ports = manager.list_ports()
    
    # The list should never be empty now
    assert len(ports) > 0
    # If it's a simulator, it must have the correct name
    if ports[0]["type"] == "SIMULATOR":
        assert ports[0]["device"] == "SIMULATOR_PORT"

def test_simulator_execution():
    manager = UARTManager()
    result = manager.run_test("SIMULATOR_PORT")
    assert result["status"] == "PASS"
