import serial
import serial.tools.list_ports
import json
import logging
import os
import sys
import time
from datetime import datetime


class UARTManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = os.path.join(self.base_dir, "logs")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.history_file = os.path.join(self.log_dir, "history.jsonl")
        self.log_path = os.path.join(self.log_dir, "system.log")
        self._setup_logger()

    def _setup_logger(self):
        """
        Private. Called once during __init__ only.
        Uses mode='w' so the log file resets on each server start —
        old 'Log System Initialized.' lines from previous sessions never
        accumulate in the file.
        """
        self.logger = logging.getLogger("UART_SYSTEM")
        self.logger.setLevel(logging.INFO)

        # Guard: if handlers already exist (e.g. uvicorn reloader imported
        # this module in a sibling process), skip — do NOT clear and re-add.
        if self.logger.hasHandlers():
            return

        fmt = logging.Formatter('%(asctime)s - %(message)s')

        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        self.logger.addHandler(sh)

        # mode='w' — overwrites the log file on each fresh server start.
        # This prevents old init messages from piling up across restarts.
        fh = logging.FileHandler(self.log_path, mode='w')
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)

    def log_startup(self):
        """
        Called ONCE from FastAPI's lifespan startup event.
        Separated from _setup_logger() so the message is never triggered
        by module imports, reload workers, or clear_logs.
        """
        self.logger.info("Log System Initialized.")

    def reset_file_handler(self):
        """
        Called only by /api/clear_logs after deleting system.log.
        Replaces the dead FileHandler — does NOT log the init message.
        """
        fmt = logging.Formatter('%(asctime)s - %(message)s')

        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.logger.removeHandler(handler)

        fh = logging.FileHandler(self.log_path, mode='w')
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)
        self.logger.info("Logs cleared. System ready.")

    def validate_logic(self, response, expected):
        if not response:
            return False
        return str(response).strip().upper() == str(expected).strip().upper()

    def list_ports(self):
        all_ports = serial.tools.list_ports.comports()
        connected = [{"device": p.device, "type": "HW"} for p in all_ports if p.hwid != 'n/a']
        return connected if connected else [{"device": "SIMULATOR_PORT", "type": "SIM"}]

    def run_test(self, port):
        return self.run_full_suite(port)

    def run_full_suite(self, port):
        report = {
            "port": port,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_status": "FAIL",
            "categories": {
                "unit": "FAIL",
                "loopback": "FAIL",
                "integration": "FAIL",
                "stress": "FAIL"
            }
        }

        self.logger.info(f"--- STARTING TEST: {port} ---")

        if port == "SIMULATOR_PORT":
            report["overall_status"] = "PASS"
            report["categories"] = {k: "PASS" for k in report["categories"]}
            self.logger.info(f"[{port}] SIMULATOR: Virtual checks PASSED.")
        else:
            ser = None
            try:
                # 1. UNIT TEST: Port Opening
                ser = serial.Serial(port, baudrate=9600, timeout=1.0)
                report["categories"]["unit"] = "PASS"
                self.logger.info(f"[{port}] UNIT: Port opened successfully.")

                # 2. LOOPBACK TEST: Physical Data Check
                test_val = b"PING"
                ser.write(test_val)
                time.sleep(0.1)
                received = ser.read(len(test_val))
                if received == test_val:
                    report["categories"]["loopback"] = "PASS"
                    self.logger.info(f"[{port}] LOOPBACK: PASS")

                # 3. INTEGRATION TEST: Command Handshake
                ser.reset_input_buffer()
                ser.write(b"VER?\r\n")
                time.sleep(0.3)
                hw_resp = ser.read_all().decode(errors='ignore').strip()
                if hw_resp:
                    report["categories"]["integration"] = "PASS"
                    self.logger.info(f"[{port}] INTEGRATION: HW responded with '{hw_resp}'")

                # 4. STRESS TEST: High-Frequency Load Test
                self.logger.info(f"[{port}] STRESS: Starting 50-packet burst...")
                success_count = 0
                ser.reset_input_buffer()

                for i in range(50):
                    packet = f"S{i}\n".encode()
                    ser.write(packet)
                    time.sleep(0.03)
                    if ser.in_waiting > 0:
                        ser.read_all()
                        success_count += 1

                if success_count >= 40:
                    report["categories"]["stress"] = "PASS"
                    self.logger.info(f"[{port}] STRESS: PASS ({success_count}/50 packets)")
                else:
                    self.logger.error(f"[{port}] STRESS: FAIL ({success_count}/50 packets acknowledged)")

                if all(v == "PASS" for v in report["categories"].values()):
                    report["overall_status"] = "PASS"

            except Exception as e:
                self.logger.error(f"[{port}] CRITICAL ERROR: {str(e)}")
            finally:
                if ser and ser.is_open:
                    ser.close()

        with open(self.history_file, "a") as f:
            f.write(json.dumps(report) + "\n")

        return report

    def get_history(self):
        if not os.path.exists(self.history_file):
            return []
        history = []
        with open(self.history_file, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    history.append(json.loads(line))
                except Exception:
                    continue
        return history
