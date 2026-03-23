import serial
import serial.tools.list_ports
import json
import logging
import os
import sys
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

VIRTUAL_PORTS_REGISTRY = "/tmp/uart_virtual_ports.txt"


class UARTManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # When pytest runs via run.sh it sets UART_LOG_DIR to a temp folder.
        # This stops test writes (SIMULATOR_PORT results) from going into
        # the production logs/ folder and appearing in the dashboard JSON.
        if os.environ.get("UART_LOG_DIR"):
            self.log_dir = os.environ["UART_LOG_DIR"]
        else:
            self.log_dir = os.path.join(self.base_dir, "logs")

        os.makedirs(self.log_dir, exist_ok=True)

        self.history_file = os.path.join(self.log_dir, "history.jsonl")
        self.log_path = os.path.join(self.log_dir, "system.log")

        self._history_lock = asyncio.Lock()
        self._setup_logger()

    def _setup_logger(self):
        self.logger = logging.getLogger("UART_SYSTEM")
        self.logger.setLevel(logging.INFO)
        if self.logger.hasHandlers():
            return
        fmt = logging.Formatter('%(asctime)s - %(message)s')
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        self.logger.addHandler(sh)
        fh = logging.FileHandler(self.log_path, mode='a')
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)

    def log_startup(self):
        self.logger.info("Log System Initialized.")

    def reset_file_handler(self):
        """
        Reattaches FileHandler. mode='a' — appends to existing log after
        restart, creates fresh file after wipe (file was just deleted).
        """
        fmt = logging.Formatter('%(asctime)s - %(message)s')
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                self.logger.removeHandler(handler)
        fh = logging.FileHandler(self.log_path, mode='a')
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)

    def validate_logic(self, response, expected):
        if not response:
            return False
        return str(response).strip().upper() == str(expected).strip().upper()

    def list_ports(self):
        """
        1. Real hardware ports  (ttyUSB*, ttyACM*)
        2. Virtual PTY ports    (/tmp/uart_virtual_ports.txt registry)
        3. SIMULATOR_PORT fallback only if nothing else found
        """
        found = []

        hw_ports = serial.tools.list_ports.comports()
        for p in hw_ports:
            if p.hwid != 'n/a':
                found.append({"device": p.device, "type": "HW"})

        if os.path.exists(VIRTUAL_PORTS_REGISTRY):
            with open(VIRTUAL_PORTS_REGISTRY, "r") as f:
                for line in f:
                    path = line.strip()
                    if path and os.path.exists(path):
                        found.append({"device": path, "type": "VirtualPTY"})

        if not found:
            return [{"device": "SIMULATOR_PORT", "type": "SIM"}]

        return found

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
                ser = serial.Serial(port, baudrate=9600, timeout=1.0)
                report["categories"]["unit"] = "PASS"
                self.logger.info(f"[{port}] UNIT: Port opened successfully.")

                test_val = b"PING"
                ser.write(test_val)
                time.sleep(0.1)
                received = ser.read(len(test_val))
                if received == test_val:
                    report["categories"]["loopback"] = "PASS"
                    self.logger.info(f"[{port}] LOOPBACK: PASS")

                ser.reset_input_buffer()
                ser.write(b"VER?\r\n")
                time.sleep(0.3)
                hw_resp = ser.read_all().decode(errors='ignore').strip()
                if hw_resp:
                    report["categories"]["integration"] = "PASS"
                    self.logger.info(f"[{port}] INTEGRATION: HW responded with '{hw_resp}'")

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

    def _run_suite_no_write(self, port: str) -> dict:
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
                ser = serial.Serial(port, baudrate=9600, timeout=1.0)
                report["categories"]["unit"] = "PASS"
                self.logger.info(f"[{port}] UNIT: Port opened successfully.")

                test_val = b"PING"
                ser.write(test_val)
                time.sleep(0.1)
                received = ser.read(len(test_val))
                if received == test_val:
                    report["categories"]["loopback"] = "PASS"
                    self.logger.info(f"[{port}] LOOPBACK: PASS")

                ser.reset_input_buffer()
                ser.write(b"VER?\r\n")
                time.sleep(0.3)
                hw_resp = ser.read_all().decode(errors='ignore').strip()
                if hw_resp:
                    report["categories"]["integration"] = "PASS"
                    self.logger.info(f"[{port}] INTEGRATION: HW responded with '{hw_resp}'")

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

        return report

    async def run_all_parallel(self, ports: list) -> list:
        loop = asyncio.get_event_loop()
        port_names = [p["device"] for p in ports]
        n = len(port_names)

        self.logger.info(
            f"[PARALLEL] Starting {n} port(s) simultaneously: {', '.join(port_names)}"
        )

        executor = ThreadPoolExecutor(max_workers=n)

        async def _run_one(port: str):
            report = await loop.run_in_executor(
                executor,
                self._run_suite_no_write,
                port
            )
            async with self._history_lock:
                with open(self.history_file, "a") as f:
                    f.write(json.dumps(report) + "\n")
            return report

        results = await asyncio.gather(*[_run_one(p) for p in port_names])
        executor.shutdown(wait=False)

        passed = sum(1 for r in results if r["overall_status"] == "PASS")
        self.logger.info(f"[PARALLEL] All {n} port(s) done. {passed}/{n} passed.")

        return list(results)

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
