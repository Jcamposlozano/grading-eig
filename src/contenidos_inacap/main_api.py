from __future__ import annotations
import os
import uvicorn
from contenidos_inacap.shared.config import load_config

def main():
    cfg = load_config()
    uvicorn.run("contenidos_inacap.entrypoints.api:app",
                host=cfg["service"]["host"],
                port=cfg["service"]["port"],
                reload=(os.getenv("ENV","dev")=="dev"))

if __name__ == "__main__":
    main()
