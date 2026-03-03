from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from .uart_manager import UARTManager
import os
import json

app = FastAPI()
manager = UARTManager()

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/scan")
def scan():
    return manager.list_ports()

@app.post("/api/test")
def test(port: str = Query(...)):
    return manager.run_test(port)

@app.get("/api/latest_report")
def get_latest_report():
    files = [os.path.join("logs", f) for f in os.listdir("logs") if f.endswith(".json")]
    if not files: return {"status": "No data found"}
    latest_file = max(files, key=os.path.getctime)
    with open(latest_file, 'r') as f:
        return json.load(f)

@app.get("/api/system_logs")
def get_system_logs():
    path = "logs/system.log"
    if not os.path.exists(path): return "No logs available."
    with open(path, "r") as f:
        return "".join(f.readlines()[-50:]) # Last 50 lines

@app.delete("/api/clear_logs")
def clear_logs():
    for f in os.listdir("logs"):
        if f.endswith(".json"): os.remove(os.path.join("logs", f))
    with open("logs/system.log", "w") as f:
        f.write("--- Logs Cleared ---\n")
    return {"message": "Logs wiped successfully"}

app.mount("/static", StaticFiles(directory="static"), name="static")
