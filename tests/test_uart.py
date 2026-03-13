import pytest
from app.uart_manager import UARTManager

def test_logic_validation():
    manager = UARTManager()
    assert manager.validate_logic("V1.0", "V1.0") is True
    assert manager.validate_logic("v1.0 ", "V1.0") is True
    assert manager.validate_logic("V2.0", "V1.0") is False

def test_simulator_execution():
    manager = UARTManager()
    result = manager.run_test("SIMULATOR_PORT")

    assert result["overall_status"] == "PASS"
    assert result["categories"]["unit"] == "PASS"
    assert result["categories"]["loopback"] == "PASS"
    assert result["categories"]["integration"] == "PASS"
    assert result["categories"]["stress"] == "PASS"

def test_history_logging():
    manager = UARTManager()
    manager.run_test("SIMULATOR_PORT")
    history = manager.get_history()
    assert len(history) > 0
    assert "categories" in history[-1]

def test_list_ports():
    manager = UARTManager()
    ports = manager.list_ports()
    assert len(ports) > 0
