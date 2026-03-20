from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _env_bool(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_config(config_dir: str = "configs") -> Dict[str, Any]:
    env = os.getenv("ENV", "dev").lower()
    base_path = BASE_DIR / config_dir / "base.yaml"
    env_path = BASE_DIR / config_dir / f"{env}.yaml"

    with base_path.open("r", encoding="utf-8") as f:
        cfg: Dict[str, Any] = yaml.safe_load(f) or {}

    if env_path.exists():
        with env_path.open("r", encoding="utf-8") as f:
            env_cfg: Dict[str, Any] = yaml.safe_load(f) or {}
        cfg = deep_merge(cfg, env_cfg)

    cfg.setdefault("project", {})
    cfg.setdefault("service", {})
    cfg.setdefault("worker", {})

    cfg["project"]["env"] = os.getenv("ENV", cfg["project"].get("env", "dev"))
    cfg["project"]["log_level"] = os.getenv("LOG_LEVEL", cfg["project"].get("log_level", "INFO"))

    cfg["service"]["host"] = os.getenv("HOST", cfg["service"].get("host", "0.0.0.0"))
    cfg["service"]["port"] = int(os.getenv("PORT", cfg["service"].get("port", 8000)))

    cfg["worker"]["enabled"] = _env_bool("WORKER_ENABLED", bool(cfg["worker"].get("enabled", True)))
    cfg["worker"]["interval_seconds"] = int(
        os.getenv("WORKER_INTERVAL_SECONDS", cfg["worker"].get("interval_seconds", 10))
    )

    return cfg