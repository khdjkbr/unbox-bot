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
    if not user_id:
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
        ''', (user_id, username or "", today))
        conn.commit()

def increment_download(user_id: int):
    if not user_id:
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
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Foydalanuvchining shaxsiy yuklab olishlari
        cursor.execute('SELECT downloads_count FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        user_downloads = user_row[0] if user_row else 1
        
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
