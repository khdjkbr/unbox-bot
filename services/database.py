import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime
import json
from urllib.request import Request, urlopen
from config import SUPABASE_URL, SUPABASE_KEY

# Render's default filesystem is ephemeral. Set DATABASE_PATH to a mounted
# persistent disk (for example /var/data/bot_database.db) in production.
DB_PATH = os.getenv("DATABASE_PATH", "downloads/bot_database.db")

def _remote():
    return bool(SUPABASE_URL and SUPABASE_KEY)

def _api(path, method="GET", payload=None, params=""):
    url = SUPABASE_URL.rstrip("/") + "/rest/v1/" + path + params
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(url, data=body, method=method, headers={
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json", "Prefer": "return=representation,resolution=merge-duplicates"})
    with urlopen(req, timeout=15) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else []

@contextmanager
def get_connection():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            yield conn
    finally:
        conn.close()

def init_db():
    if _remote():
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                joined_at DATE,
                downloads_count INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

def add_user(user_id: int, username: str = None):
    if not user_id:
        return
    if _remote():
        _api("users", "POST", {"user_id": user_id, "username": username,
              "joined_at": datetime.now().strftime("%Y-%m-%d"), "downloads_count": 0},
             "?on_conflict=user_id")
        return
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('''
            INSERT INTO users (user_id, username, joined_at, downloads_count)
            VALUES (?, ?, ?, 0)
            ON CONFLICT(user_id) DO UPDATE SET
            username = COALESCE(excluded.username, users.username)
        ''', (user_id, username, today))
        conn.commit()

def increment_download(user_id: int):
    if not user_id:
        return
    if _remote():
        rows = _api("users", params=f"?user_id=eq.{user_id}&select=downloads_count")
        if rows:
            _api("users", "PATCH", {"downloads_count": rows[0]["downloads_count"] + 1},
                 f"?user_id=eq.{user_id}")
        return
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET downloads_count = downloads_count + 1 
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()

def get_user_and_global_stats(user_id: int):
    if _remote():
        users = _api("users", params="?select=downloads_count")
        mine = _api("users", params=f"?user_id=eq.{user_id}&select=downloads_count")
        return {"user_downloads": mine[0]["downloads_count"] if mine else 0,
                "total_users": len(users),
                "total_downloads": sum(u.get("downloads_count", 0) or 0 for u in users)}
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Foydalanuvchining shaxsiy yuklab olishlari
        cursor.execute('SELECT downloads_count FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        user_downloads = user_row[0] if user_row else 0
        
        # Jami barcha foydalanuvchilar (guruhdagilar + lichkadagilar)
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        # Jami barcha yuklab olishlar
        cursor.execute('SELECT SUM(downloads_count) FROM users')
        row = cursor.fetchone()
        total_downloads = row[0] if (row and row[0] is not None) else 0

        return {
            "user_downloads": user_downloads,
            "total_users": total_users,
            "total_downloads": total_downloads
        }

def get_stats():
    if _remote():
        users = _api("users", params="?select=joined_at,downloads_count")
        today = datetime.now().strftime("%Y-%m-%d")
        return {"total_users": len(users), "today_users": sum(1 for u in users if u.get("joined_at") == today),
                "total_downloads": sum(u.get("downloads_count", 0) or 0 for u in users)}
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('SELECT COUNT(*) FROM users WHERE joined_at = ?', (today,))
        today_users = cursor.fetchone()[0]

        cursor.execute('SELECT SUM(downloads_count) FROM users')
        row = cursor.fetchone()
        total_downloads = row[0] if (row and row[0] is not None) else 0

        return {
            "total_users": total_users,
            "today_users": today_users,
            "total_downloads": total_downloads
        }
