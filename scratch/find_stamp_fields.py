import sqlite3
import os

db_path = r"c:\pinchus\Projects\123\data\stamps.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Search stamps table for any text containing the UUID
    cur.execute("SELECT * FROM stamps WHERE project='123'")
    stamps = cur.fetchall()
    print("Checking stamps table...")
    for s in stamps:
        s_dict = dict(s)
        for k, v in s_dict.items():
            if str(v) == '39752c07-8007-4c95-bae5-ab63102a9134':
                print(f"Match in stamps table: {s_dict}")
                
    # Search stamp_fields table
    cur.execute("SELECT * FROM stamp_fields WHERE value='39752c07-8007-4c95-bae5-ab63102a9134' OR name='39752c07-8007-4c95-bae5-ab63102a9134'")
    fields = cur.fetchall()
    print("Checking stamp_fields table...")
    for f in fields:
        print(dict(f))
        
    conn.close()
else:
    print("Database not found")
