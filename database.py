import os, json, logging
from pathlib import Path

logger = logging.getLogger(__name__)
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data" if os.path.isdir("/data") else "./data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE  = DATA_DIR / "users.json"
BATCHES_FILE = DATA_DIR / "batches.json"
VIDEOS_FILE = DATA_DIR / "videos.json"

def _load(path):
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception:
        return {}

def _save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False))

class Database:
    def get_user(self, user_id, default=None):
        return _load(USERS_FILE).get(str(user_id), default)

    def save_user(self, user_id, data):
        db = _load(USERS_FILE)
        db[str(user_id)] = data
        _save(USERS_FILE, db)

    def delete_user(self, user_id):
        for f in [USERS_FILE, BATCHES_FILE]:
            db = _load(f)
            db.pop(str(user_id), None)
            _save(f, db)

    def save_batches(self, user_id, batches):
        db = _load(BATCHES_FILE)
        db[str(user_id)] = batches
        _save(BATCHES_FILE, db)

    def get_batches(self, user_id):
        return _load(BATCHES_FILE).get(str(user_id), [])

    def save_video(self, video_id, data):
        db = _load(VIDEOS_FILE)
        db[str(video_id)] = data
        _save(VIDEOS_FILE, db)

    def get_video(self, video_id):
        return _load(VIDEOS_FILE).get(str(video_id))
