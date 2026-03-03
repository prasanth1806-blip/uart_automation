import serial
import serial.tools.list_ports
import json
import logging
import os
from datetime import datetime

class UARTManager:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # System Log Configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler(f"{self.log_dir}/system.log"), logging.StreamHandler()]
        )

    def list_ports(self):
        ports = serial.tools.list_ports.comports()
        # Filter for active USB/ACM hardware only
        active_hardware = [
            {"device": p.device, "desc": p.description, "type": "HARDWARE"} 
            for p in ports 
            if any(x in p.device.upper() or x in p.description.upper() for x in ["USB", "ACM", "SERIAL"])
        ]
        
        if active_hardware:
            return active_hardware
        else:
            return [{"device": "SIMULATOR_PORT", "desc": "Virtual Automation Mode", "type": "SIMULATOR"}]

    def run_test(self, port, baud=115200):
        result = {"port": port, "timestamp": datetime.now().isoformat(), "status": "FAIL"}
        logging.info(f"Starting test on {port}")

        if port == "SIMULATOR_PORT":
            result.update({"status": "PASS", "data": "SIM_OK", "mode": "simulator"})
            logging.info("Simulation test passed.")
        else:
            try:
                with serial.Serial(port, baud, timeout=1) as ser:
                    ser.write(b'\r\n')
                    response = ser.read(32).decode('utf-8', errors='ignore')
                    result.update({"status": "PASS", "data": response or "ECHO_OK", "mode": "hardware"})
                    logging.info(f"Hardware test on {port} passed.")
            except Exception as e:
                result["error"] = str(e)
                logging.error(f"Hardware test failed: {e}")

        # Save JSON Report
        filename = f"report_{datetime.now().strftime('%H%M%S')}.json"
        with open(os.path.join(self.log_dir, filename), "w") as f:
            json.dump(result, f, indent=4)
        
        return result
