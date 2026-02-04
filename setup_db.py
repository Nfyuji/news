import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = 'news_bot.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # جدول الأخبار (موجود سابقاً - نحدثه إذا لزم)
    c.execute('''CREATE TABLE IF NOT EXISTS published_news
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT UNIQUE,
                  source TEXT,
                  link TEXT,
                  published_at TIMESTAMP,
                  telegram_message_id INTEGER,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # جدول المستخدمين (للدخول للوحة التحكم)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL)''')

    # جدول المصادر (RSS Feeds) - لكي نتحكم بها من اللوحة
    c.execute('''CREATE TABLE IF NOT EXISTS rss_feeds
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  url TEXT NOT NULL UNIQUE,
                  is_active BOOLEAN DEFAULT 1,
                  added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # إضافة مستخدم افتراضي إذا لم يوجد
    try:
        # Default: admin / admin123
        password = generate_password_hash("admin123")
        c.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)", 
                 ("admin", password))
        print("[OK] Added default user: admin / admin123")
    except Exception as e:
        print(f"User creation info: {e}")

    # نقل المصادر من config.py إلى قاعدة البيانات (مرة واحدة)
    try:
        from config import RSS_FEEDS
        print("Migrating feeds from config.py...")
        count = 0
        for name, url in RSS_FEEDS.items():
            try:
                c.execute("INSERT OR IGNORE INTO rss_feeds (name, url) VALUES (?, ?)", (name, url))
                count += 1
            except:
                pass
        print(f"[OK] Migrated {count} feeds to database.")
    except ImportError:
        print("Config file not found or empty, skipping migration.")

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully.")

if __name__ == "__main__":
    init_db()
