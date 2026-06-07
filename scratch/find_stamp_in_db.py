import sqlite3
import os

db_path = r"c:\pinchus\Projects\123\data\stamps.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM stamps WHERE pdf_path LIKE '%QCC_Mechanical%' LIMIT 5")
    rows = cur.fetchall()
    print("Found stamps for QCC_Mechanical in DB:")
    for row in rows:
        print(dict(row))
    conn.close()
else:
    print("Database not found at:", db_path)
