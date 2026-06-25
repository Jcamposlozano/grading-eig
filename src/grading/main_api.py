from __future__ import annotations

import os

import uvicorn

from grading.shared.config import load_config


def main():
    cfg = load_config()
    uvicorn.run(
        "grading.entrypoints.api:app",
        host=cfg["service"]["host"],
        port=cfg["service"]["port"],
        reload=(os.getenv("ENV", "dev") == "dev"),
    )


if __name__ == "__main__":
    main()
