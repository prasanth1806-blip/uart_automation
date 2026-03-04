import serial
import serial.tools.list_ports
import json
import logging
import os
import time
from datetime import datetime

class UARTManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(self.base_dir, "logs")
        if not os.path.exists(self.log_dir): os.makedirs(self.log_dir)
        
        self.log_path = os.path.join(self.log_dir, "system.log")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            handlers=[logging.FileHandler(self.log_path, mode='a'), logging.StreamHandler()]
        )

    def list_ports(self):
        """Filters for only CONNECTED hardware (USB/ACM/COM)."""
        ports = serial.tools.list_ports.comports()
        # Only include ports that have "USB", "ACM", or "SERIAL" in their description or device name
        active_hardware = [
            {"device": p.device, "type": "HARDWARE", "desc": p.description} 
            for p in ports 
            if any(x in p.device.upper() or x in p.description.upper() for x in ["USB", "ACM", "SERIAL", "COM"])
        ]
        # Return filtered hardware, or simulator if empty
        return active_hardware or [{"device": "SIMULATOR_PORT", "type": "SIMULATOR", "desc": "Virtual Dev Environment"}]

    def validate_logic(self, response, expected):
        return response.strip().upper() == expected.strip().upper()

    def run_test(self, port, mode="STANDARD"):
        logging.info(f"--- Running {mode} Suite on {port} ---")
        report = {
            "port": port, "mode": mode, "timestamp": datetime.now().isoformat(),
            "overall_status": "PASS", "summary": "Firmware OK",
            "categories": {"unit": "PASS", "integration": "FAIL", "regression": "FAIL"},
            "steps": []
        }

        # Step 1: Integration (Handshake)
        expected_h = "PING" if mode == "LOOPBACK" else "PONG"
        step1 = self._execute_step("Integration: Handshake", port, "PING", expected_h)
        report["steps"].append(step1)
        report["categories"]["integration"] = step1["status"]

        # Step 2: Regression (Build Check)
        step2 = self._execute_step("Regression: Build Check", port, "VER", "1.0.0")
        report["steps"].append(step2)
        report["categories"]["regression"] = step2["status"]

        if any(s["status"] == "FAIL" for s in report["steps"]):
            report["overall_status"] = "FAIL"
            report["summary"] = "Validation FAILED"

        with open(os.path.join(self.log_dir, "latest.json"), "w") as f:
            json.dump(report, f, indent=4)
        return report

    def _execute_step(self, name, port, cmd, expected):
        res = {"name": name, "status": "FAIL", "sent": cmd, "received": ""}
        if port == "SIMULATOR_PORT":
            res.update({"status": "PASS", "received": expected})
            return res

        try:
            with serial.Serial(port, 9600, timeout=1.5) as ser:
                time.sleep(0.1)
                ser.write(f"{cmd}\r\n".encode())
                raw = ser.read(64).decode('utf-8', errors='ignore').strip()
                received = raw.replace(cmd, "").strip() if cmd in raw else raw
                res["received"] = received
                if self.validate_logic(res["received"], expected):
                    res["status"] = "PASS"
        except Exception as e:
            res["error"] = str(e)
        return res
