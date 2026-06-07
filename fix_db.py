import sqlite3
import re

conn = sqlite3.connect(r'c:\pinchus\Projects\Test\data\stamps.db')
cur = conn.cursor()
cur.execute('SELECT id, pattern_name FROM stamps')
rows = cur.fetchall()

updates = []
for stamp_id, pat in rows:
    if not pat:
        continue
    m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', pat)
    if m:
        num = m.group(2)
    else:
        num = pat
    updates.append((num, stamp_id, '#'))

cur.executemany('UPDATE stamp_fields SET value=? WHERE stamp_id=? AND name=?', updates)
conn.commit()
conn.close()
print("Fixed DB")
