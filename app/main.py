from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from .uart_manager import UARTManager
import os

manager = UARTManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs ONCE when the uvicorn worker starts.

    ✅ Clears history.jsonl on every server start so stale results
    from previous sessions (e.g. old SIMULATOR_PORT runs logged before
    a real USB port was plugged in) never bleed into a fresh session.

    System log is also reset so it reflects only the current session.
    """
    # Wipe stale history from previous server session
    if os.path.exists(manager.history_file):
        os.remove(manager.history_file)

    # Wipe stale log file and reattach a fresh FileHandler
    if os.path.exists(manager.log_path):
        os.remove(manager.log_path)
    manager.reset_file_handler()

    # Single init message — fires exactly once per server start
    manager.log_startup()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse('static/index.html')


@app.get("/api/scan")
def scan():
    """
    Detects available ports only.
    Returns HW ports if found, SIMULATOR_PORT only if nothing is connected.
    Never triggers a test.
    """
    return manager.list_ports()


@app.post("/api/test")
def test(port: str):
    """Run tests on a single specific port."""
    return manager.run_full_suite(port)


@app.post("/api/test_all")
def test_all():
    """
    Run tests on ALL currently detected ports.
    If a real HW port is found, SIMULATOR_PORT is excluded automatically
    by list_ports() — simulator only runs when no HW port is present.
    """
    ports = manager.list_ports()
    for p in ports:
        manager.run_full_suite(p['device'])
    return {"status": "Complete"}


@app.get("/api/history")
def history():
    return manager.get_history()


@app.get("/api/system_logs", response_class=PlainTextResponse)
def logs():
    if not os.path.exists(manager.log_path):
        return "Waiting for logs..."
    with open(manager.log_path, "r") as f:
        return "".join(f.readlines()[-100:])


@app.delete("/api/clear_logs")
def clear():
    """Wipes history and log files, reattaches a fresh FileHandler."""
    if os.path.exists(manager.history_file):
        os.remove(manager.history_file)
    if os.path.exists(manager.log_path):
        os.remove(manager.log_path)
    manager.reset_file_handler()
    return {"status": "success"}


app.mount("/static", StaticFiles(directory="static"), name="static")
