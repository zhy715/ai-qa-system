"""Direct server runner — bypass uvicorn CLI issues"""
import os
os.environ["HF_HUB_OFFLINE"] = "1"

import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
