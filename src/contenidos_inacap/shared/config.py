from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[3]
ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


def deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
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


def load_config(config_dir: str = "configs") -> dict[str, Any]:
    env = os.getenv("ENV", "dev").lower()
    base_path = BASE_DIR / config_dir / "base.yaml"
    env_path = BASE_DIR / config_dir / f"{env}.yaml"

    with base_path.open("r", encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f) or {}

    if env_path.exists():
        with env_path.open("r", encoding="utf-8") as f:
            env_cfg: dict[str, Any] = yaml.safe_load(f) or {}
        cfg = deep_merge(cfg, env_cfg)

    cfg.setdefault("project", {})
    cfg.setdefault("service", {})
    cfg.setdefault("worker", {})
    cfg.setdefault("storage", {})
    cfg.setdefault("credentials", {})
    cfg.setdefault("queue", {})

    cfg["project"]["env"] = os.getenv("ENV", cfg["project"].get("env", "dev"))
    cfg["project"]["log_level"] = os.getenv("LOG_LEVEL", cfg["project"].get("log_level", "INFO"))

    cfg["service"]["host"] = os.getenv("HOST", cfg["service"].get("host", "0.0.0.0"))
    cfg["service"]["port"] = int(os.getenv("PORT", cfg["service"].get("port", 8000)))

    cfg["worker"]["enabled"] = _env_bool("WORKER_ENABLED", bool(cfg["worker"].get("enabled", True)))
    cfg["worker"]["interval_seconds"] = int(
        os.getenv("WORKER_INTERVAL_SECONDS", cfg["worker"].get("interval_seconds", 10))
    )

    cfg["storage"]["backend"] = os.getenv("STORAGE_BACKEND", cfg["storage"].get("backend", "local"))
    cfg["storage"]["local_base_dir"] = os.getenv(
        "STORAGE_LOCAL_DIR", cfg["storage"].get("local_base_dir", "data/objects")
    )
    cfg["storage"]["s3_bucket"] = os.getenv("S3_BUCKET", cfg["storage"].get("s3_bucket"))
    cfg["storage"]["region"] = os.getenv("AWS_REGION", cfg["storage"].get("region"))

    cfg["credentials"]["backend"] = os.getenv(
        "CREDENTIALS_BACKEND", cfg["credentials"].get("backend", "env")
    )
    cfg["credentials"]["secret_prefix"] = os.getenv(
        "CANVAS_SECRET_PREFIX", cfg["credentials"].get("secret_prefix", "prisma/grading")
    )

    cfg["queue"]["backend"] = os.getenv("QUEUE_BACKEND", cfg["queue"].get("backend", "memory"))
    cfg["queue"]["url"] = os.getenv("SQS_QUEUE_URL", cfg["queue"].get("url"))
    cfg["queue"]["wait_seconds"] = int(
        os.getenv("QUEUE_WAIT_SECONDS", cfg["queue"].get("wait_seconds", 20))
    )
    cfg["queue"]["max_messages"] = int(
        os.getenv("QUEUE_MAX_MESSAGES", cfg["queue"].get("max_messages", 5))
    )

    return cfg
