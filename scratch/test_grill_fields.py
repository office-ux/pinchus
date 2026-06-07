import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_viewer'))

import stamp_db

def test_defaults():
    print("Initializing test stamp...")
    # Initialize DB (if not already done)
    stamp_db.init_db()
    
    # Get or create a test stamp
    project = "TestProject"
    pdf_path = "test_doc.pdf"
    page = 1
    xref = 9999
    
    # Check stamp creation
    stamp_id = stamp_db.get_or_create_stamp(project, pdf_path, page, xref)
    print(f"Stamp created with ID: {stamp_id}")
    
    # Check default metadata retrieval
    meta = stamp_db.get_stamp_metadata(stamp_id)
    fields = meta["fields"]
    
    print(f"Retrieved {len(fields)} fields:")
    for f in fields:
        print(f"  - {f['name']}: '{f['value']}' ({f['type']})")
        
    # Check if we have the hashtag field
    has_hashtag = any(f["name"] == "#" for f in fields)
    print(f"Has hashtag field: {has_hashtag}")
    
    # Clean up test entry
    conn = stamp_db._get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM stamp_fields WHERE stamp_id=?", (stamp_id,))
        cur.execute("DELETE FROM stamps WHERE id=?", (stamp_id,))
        conn.commit()
        print("Cleanup successful.")
    finally:
        conn.close()

if __name__ == "__main__":
    test_defaults()
