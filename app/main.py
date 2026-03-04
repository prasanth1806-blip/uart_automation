import os
import glob
from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from .uart_manager import UARTManager

app = FastAPI()
manager = UARTManager()

# ... (keep your existing @app.get routes) ...

@app.delete("/api/clear_logs")
def clear_logs():
    """Deletes all log files and test reports."""
    files = glob.glob("logs/*.log") + glob.glob("logs/*.json")
    for f in files:
        try:
            os.remove(f)
        except:
            pass
    return {"status": "success", "message": "Logs cleared"}

app.mount("/static", StaticFiles(directory="static"), name="static")
