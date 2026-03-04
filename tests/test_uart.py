import pytest
from app.uart_manager import UARTManager

def test_logic_validation():
    manager = UARTManager()
    # Unit Test: Logic check
    assert manager.validate_logic("PONG", "PONG") is True
    assert manager.validate_logic("FAIL", "PONG") is False

def test_simulator_execution():
    manager = UARTManager()
    # Integration/Regression Test via Simulator
    result = manager.run_test("SIMULATOR_PORT")
    assert result["overall_status"] == "PASS"
    assert result["categories"]["integration"] == "PASS"
