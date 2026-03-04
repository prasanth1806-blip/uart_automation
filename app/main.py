from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from .uart_manager import UARTManager
import os

app = FastAPI()
manager = UARTManager()

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
def test_all():
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
        # Returns the last 100 lines for the Terminal UI
        return "".join(f.readlines()[-100:])

@app.delete("/api/clear_logs")
def clear():
    if os.path.exists(manager.history_file): os.remove(manager.history_file)
    if os.path.exists(manager.log_path): os.remove(manager.log_path)
    manager.setup_logger()
    return {"status": "success"}

app.mount("/static", StaticFiles(directory="static"), name="static")
