from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from .uart_manager import UARTManager
import os, json

app = FastAPI()
manager = UARTManager()

@app.get("/")
async def root(): return RedirectResponse(url="/static/index.html")

@app.get("/api/scan")
def scan(): return manager.list_ports()

@app.post("/api/test")
def test(port: str = Query(...)): return manager.run_test(port)

@app.get("/api/latest_report")
def get_latest_report():
    files = [os.path.join("logs", f) for f in os.listdir("logs") if f.startswith("report_")]
    if not files: return {"status": "No data"}
    latest = max(files, key=os.path.getctime)
    with open(latest, 'r') as f: return json.load(f)

@app.get("/api/system_logs")
def get_logs():
    path = "logs/system.log"
    if not os.path.exists(path): return "No logs."
    with open(path, "r") as f: return "".join(f.readlines()[-50:])

@app.delete("/api/clear_logs")
def clear():
    for f in os.listdir("logs"): os.remove(os.path.join("logs", f))
    return {"message": "Wiped"}

app.mount("/static", StaticFiles(directory="static"), name="static")
