import sqlite3
import os

db_path = r"c:\pinchus\web_viewer\stamps.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print("TABLES:", [r[0] for r in cur.fetchall()])
    conn.close()
else:
    print("Database not found!")
