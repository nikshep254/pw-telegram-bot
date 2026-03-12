"""
Simple JSON-based persistent storage for user sessions & batch cache.
On Railway, all data lives in /data (Railway persistent volume) if available,
otherwise falls back to local directory.
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data" if os.path.isdir("/data") else "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
BATCHES_FILE = DATA_DIR / "batches.json"


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def _save(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False))


class Database:
    # ── Users ─────────────────────────────────────────────────────────────────

    def get_user(self, user_id: int) -> dict | None:
        db = _load(USERS_FILE)
        return db.get(str(user_id))

    def save_user(self, user_id: int, data: dict):
        db = _load(USERS_FILE)
        db[str(user_id)] = data
        _save(USERS_FILE, db)
        logger.info(f"Saved user {user_id}")

    def delete_user(self, user_id: int):
        db = _load(USERS_FILE)
        db.pop(str(user_id), None)
        _save(USERS_FILE, db)
        # Also clear batches cache
        bdb = _load(BATCHES_FILE)
        bdb.pop(str(user_id), None)
        _save(BATCHES_FILE, bdb)

    # ── Batches cache ─────────────────────────────────────────────────────────

    def save_batches(self, user_id: int, batches: list):
        db = _load(BATCHES_FILE)
        db[str(user_id)] = batches
        _save(BATCHES_FILE, db)

    def get_batches(self, user_id: int) -> list:
        db = _load(BATCHES_FILE)
        return db.get(str(user_id), [])
