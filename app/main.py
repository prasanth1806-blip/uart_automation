from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from .uart_manager import UARTManager
import os

manager = UARTManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.path.exists(manager.history_file):
        os.remove(manager.history_file)
    if os.path.exists(manager.log_path):
        os.remove(manager.log_path)
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
    """Single port — unchanged, still runs sequentially."""
    return manager.run_full_suite(port)


@app.post("/api/test_all")
async def test_all():
    """
    Changed from 'def' to 'async def'.

    Old behaviour: for-loop calling run_full_suite() one port at a time —
    the entire server blocked until every port finished sequentially.

    New behaviour: calls run_all_parallel() which uses ThreadPoolExecutor
    + asyncio.gather to run all ports simultaneously in separate threads.
    The event loop stays free so log polling and other requests still work
    while tests are running. Total time = slowest single port, not the sum.
    """
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
        return "".join(f.readlines()[-100:])


@app.delete("/api/clear_logs")
def clear():
    if os.path.exists(manager.history_file):
        os.remove(manager.history_file)
    if os.path.exists(manager.log_path):
        os.remove(manager.log_path)
    manager.reset_file_handler()
    return {"status": "success"}


app.mount("/static", StaticFiles(directory="static"), name="static")
