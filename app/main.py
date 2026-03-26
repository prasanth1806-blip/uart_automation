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
    Completely minimal startup — only attaches the file handler.
    No flag files, no startup messages, no test triggers.
    The double 'Log System Initialized.' was caused by a race condition:
    two uvicorn workers checking os.path.exists() at the same millisecond
    before either had written the flag file.

    Solution: remove the flag entirely. Just attach the handler and write
    one log line unconditionally. Two workers = two lines is acceptable
    and harmless. The real bug (SIMULATOR_PORT auto-running) is NOT here —
    it is in run.sh running pytest before uvicorn starts, and pytest
    instantiates UARTManager which calls run_test via test_simulator_execution.
    """
    manager.reset_file_handler()
    manager.log_startup()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def index():
    return FileResponse('static/index.html')


@app.get("/api/scan")
def scan():
    return manager.list_ports()


@app.post("/api/test")
def test(port: str):
    return manager.run_full_suite(port)


@app.post("/api/test_all")
async def test_all():
    ports = manager.list_ports()
    results = await manager.run_all_parallel(ports)
    return {"status": "Complete", "count": len(results)}


@app.get("/api/history")
def history():
    return manager.get_history()


@app.get("/api/system_logs", response_class=PlainTextResponse)
def logs():
    if not os.path.exists(manager.log_path):
        return "Waiting for logs..."
    with open(manager.log_path, "r") as f:
        return "".join(f.readlines()[-10000:])


@app.delete("/api/clear_logs")
def clear():
    """Wipes ALL files in logs/ — both system.log and history.jsonl."""
    if os.path.isdir(manager.log_dir):
        for filename in os.listdir(manager.log_dir):
            filepath = os.path.join(manager.log_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)
    manager.reset_file_handler()
    manager.log_startup()
    return {"status": "success"}


app.mount("/static", StaticFiles(directory="static"), name="static")
