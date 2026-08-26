import sqlite3
import os
from datetime import datetime

DB_PATH = "downloads/bot_database.db"

def get_connection():
    os.makedirs("downloads", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
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
    with get_connection() as conn:
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, joined_at, downloads_count)
            VALUES (?, ?, ?, 0)
        ''', (user_id, username or "", today))
        conn.commit()

def increment_download(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET downloads_count = downloads_count + 1 
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()

def get_stats():
    with get_connection() as conn:
        cursor = conn.cursor()
        # Jami foydalanuvchilar
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]

        # Bugun qo'shilganlar
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('SELECT COUNT(*) FROM users WHERE joined_at = ?', (today,))
        today_users = cursor.fetchone()[0]

        # Jami yuklab olishlar
        cursor.execute('SELECT SUM(downloads_count) FROM users')
        total_downloads = cursor.fetchone()[0] or 0

        return {
            "total_users": total_users,
            "today_users": today_users,
            "total_downloads": total_downloads
        }
