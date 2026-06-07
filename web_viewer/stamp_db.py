import os
import sqlite3
import threading
import re
from typing import List, Dict, Any, Optional

_lock = threading.Lock()
_initialized_projects = set()

def get_db_path(project: str) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Sanitize project just in case
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project).strip()
    if not sanitized_proj:
        sanitized_proj = "default"
    db_dir = os.path.join(base_dir, 'Projects', sanitized_proj, 'data')
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, 'stamps.db')

def _get_connection(project: str) -> sqlite3.Connection:
    db_path = get_db_path(project)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    
    if project not in _initialized_projects:
        _init_project_db(conn, project)
    
    return conn

def _init_project_db(conn: sqlite3.Connection, project: str):
    try:
        cur = conn.cursor()
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS stamps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                pdf_path TEXT NOT NULL,
                page INTEGER NOT NULL,
                xref INTEGER NOT NULL,
                UNIQUE(project, pdf_path, page, xref)
            );
            CREATE TABLE IF NOT EXISTS stamp_fields (
                stamp_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                value TEXT,
                type TEXT CHECK(type IN ("string", "number")) NOT NULL,
                PRIMARY KEY (stamp_id, name),
                FOREIGN KEY (stamp_id) REFERENCES stamps(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS stamp_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                name TEXT NOT NULL,
                color TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stamp_group_assignments (
                stamp_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                PRIMARY KEY (stamp_id),
                FOREIGN KEY (stamp_id) REFERENCES stamps(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES stamp_groups(id) ON DELETE CASCADE
            );
        ''')
        
        # Migration: add stamp_type if not exists
        try:
            cur.execute("ALTER TABLE stamps ADD COLUMN stamp_type TEXT DEFAULT 'air_outlet'")
        except sqlite3.OperationalError:
            pass # Column already exists
        
        # Migration: add pdf_name and pdf_uuid
        try:
            cur.execute("ALTER TABLE stamps ADD COLUMN pdf_name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE stamps ADD COLUMN pdf_uuid TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Migration: add pattern_name
        try:
            cur.execute("ALTER TABLE stamps ADD COLUMN pattern_name TEXT")
        except sqlite3.OperationalError:
            pass
            
        # Migration: add stamp_uuid
        try:
            cur.execute("ALTER TABLE stamps ADD COLUMN stamp_uuid TEXT")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
        _initialized_projects.add(project)
    except Exception as e:
        print(f"Error initializing DB for project {project}: {e}")

def normalize_db_path(path: str) -> str:
    if not path:
        return path
    p = os.path.normpath(path).replace('/', '\\')
    if len(p) >= 2 and p[1] == ':' and p[0].isalpha():
        p = p[0].upper() + p[1:]
    return p

def get_or_create_stamp(project: str, pdf_path: str, page: int, xref: int, pdf_name: str = None, pdf_uuid: str = None, stamp_type: str = None, pattern_name: str = None, stamp_uuid: str = None) -> int:
    pdf_path = normalize_db_path(pdf_path)
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, pdf_name, pdf_uuid, stamp_type, pattern_name, stamp_uuid FROM stamps WHERE project=? AND pdf_path=? AND page=? AND xref=?",
                (project, pdf_path, page, xref)
            )
            row = cur.fetchone()
            if row:
                stamp_id = row["id"]
                updates = []
                params = []
                if pdf_name is not None and row["pdf_name"] != pdf_name:
                    updates.append("pdf_name=?")
                    params.append(pdf_name)
                if pdf_uuid is not None and row["pdf_uuid"] != pdf_uuid:
                    updates.append("pdf_uuid=?")
                    params.append(pdf_uuid)
                if stamp_type is not None and row["stamp_type"] != stamp_type:
                    if not row["stamp_type"] or (stamp_type == "system" and row["stamp_type"] == "air_outlet"):
                        updates.append("stamp_type=?")
                        params.append(stamp_type)
                if pattern_name is not None and row["pattern_name"] != pattern_name:
                    if not row["pattern_name"]: # Do not overwrite if DB already has a value
                        updates.append("pattern_name=?")
                        params.append(pattern_name)
                if stamp_uuid is not None and row["stamp_uuid"] != stamp_uuid:
                    updates.append("stamp_uuid=?")
                    params.append(stamp_uuid)
                
                if updates:
                    params.append(stamp_id)
                    cur.execute(f"UPDATE stamps SET {','.join(updates)} WHERE id=?", params)
                    conn.commit()
                return stamp_id

            cur.execute(
                "INSERT INTO stamps (project, pdf_path, page, xref, pdf_name, pdf_uuid, stamp_type, pattern_name, stamp_uuid) VALUES (?,?,?,?,?,?,?,?,?)",
                (project, pdf_path, page, xref, pdf_name, pdf_uuid, stamp_type or 'air_outlet', pattern_name, stamp_uuid)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()



import json

def _get_data_viewer_defaults():
    config_path = r"c:\pinchus\config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("data_viewer", {})
        except Exception as e:
            pass
    return {}

def get_stamp_metadata(project: str, stamp_id: int) -> Dict[str, Any]:
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("SELECT stamp_type FROM stamps WHERE id=?", (stamp_id,))
            stamp_row = cur.fetchone()
            stamp_type = stamp_row["stamp_type"] if stamp_row else "air_outlet"

            cur.execute("SELECT * FROM stamp_fields WHERE stamp_id=?", (stamp_id,))
            fields = [dict(row) for row in cur.fetchall()]
            
            if not fields:
                dv_config = _get_data_viewer_defaults()
                if stamp_type == "system":
                    defaults = dv_config.get("system_fields", [{"name": "#", "type": "string", "value": ""}])
                else:
                    defaults = dv_config.get("air_outlet_fields", [{"name": "#", "type": "string", "value": ""}])
                    
                for f in defaults:
                    cur.execute(
                        "INSERT INTO stamp_fields (stamp_id, name, value, type) VALUES (?,?,?,?)",
                        (stamp_id, f.get("name", ""), f.get("value", ""), f.get("type", "string"))
                    )
                conn.commit()
                cur.execute("SELECT * FROM stamp_fields WHERE stamp_id=?", (stamp_id,))
                fields = [dict(row) for row in cur.fetchall()]

            # Auto-inject or fill # field if empty
            cur.execute("SELECT pattern_name FROM stamps WHERE id=?", (stamp_id,))
            pat_row = cur.fetchone()
            pat_name = pat_row["pattern_name"] if pat_row and pat_row["pattern_name"] else ""
            
            import re
            m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', pat_name)
            if m:
                base_pat = m.group(1)
                auto_num = m.group(2)
            else:
                base_pat = pat_name
                auto_num = pat_name

            hash_field_name = "#"
            has_hash = False
            for f in fields:
                if f["name"] == hash_field_name:
                    has_hash = True
                    if not f["value"]:
                        f["value"] = auto_num
                    break
            
            if not has_hash:
                # If they completely deleted it, we re-inject it so it always exists
                fields.insert(0, {"name": hash_field_name, "value": auto_num, "type": "string"})

            cur.execute(
                "SELECT g.id, g.name, g.color FROM stamp_groups g "
                "JOIN stamp_group_assignments a ON a.group_id = g.id WHERE a.stamp_id=?",
                (stamp_id,)
            )
            group = cur.fetchone()
            
            cur.execute("SELECT pdf_name, pdf_uuid FROM stamps WHERE id=?", (stamp_id,))
            pdf_info_row = cur.fetchone()
            pdf_name = pdf_info_row["pdf_name"] if pdf_info_row else None
            pdf_uuid = pdf_info_row["pdf_uuid"] if pdf_info_row else None
            
            return {
                "fields": fields, 
                "group": dict(group) if group else None, 
                "stamp_type": stamp_type,
                "pdf_name": pdf_name,
                "pdf_uuid": pdf_uuid,
                "pattern_name": base_pat,
                "full_pattern_name": pat_name
            }
        finally:
            conn.close()

def upsert_fields(project: str, stamp_id: int, fields: List[Dict[str, Any]]):
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM stamp_fields WHERE stamp_id=?", (stamp_id,))
            for f in fields:
                cur.execute(
                    "INSERT INTO stamp_fields (stamp_id, name, value, type) VALUES (?,?,?,?)",
                    (stamp_id, f.get('name'), f.get('value'), f.get('type', 'string'))
                )
            conn.commit()
        finally:
            conn.close()

def update_stamp_type(project: str, stamp_id: int, stamp_type: str):
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("UPDATE stamps SET stamp_type=? WHERE id=?", (stamp_type, stamp_id))
            conn.commit()
        finally:
            conn.close()

def assign_group(project: str, stamp_id: int, group_id: Optional[int]):
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM stamp_group_assignments WHERE stamp_id=?", (stamp_id,))
            if group_id:
                cur.execute(
                    "INSERT INTO stamp_group_assignments (stamp_id, group_id) VALUES (?,?)",
                    (stamp_id, group_id)
                )
            conn.commit()
        finally:
            conn.close()

def list_groups(project: str) -> List[Dict[str, Any]]:
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM stamp_groups WHERE project=? ORDER BY name", (project,))
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

def create_group(project: str, name: str, color: str) -> int:
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO stamp_groups (project, name, color) VALUES (?,?,?)",
                (project, name, color)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

def delete_stamp_record(project: str, pdf_path: str, xref: int):
    pdf_path = normalize_db_path(pdf_path)
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM stamps WHERE pdf_path=? AND xref=?", (pdf_path, xref))
            conn.commit()
        finally:
            conn.close()

def delete_all_pdf_stamps(project: str, pdf_path: str):
    pdf_path = normalize_db_path(pdf_path)
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM stamps WHERE pdf_path=?", (pdf_path,))
            conn.commit()
        finally:
            conn.close()

def get_all_project_fields(project: str) -> List[str]:
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT f.name
                FROM stamp_fields f
                JOIN stamps s ON s.id = f.stamp_id
                WHERE s.project = ? AND f.name IS NOT NULL
                """,
                (project,)
            )
            return [row["name"] for row in cur.fetchall()]
        finally:
            conn.close()

def get_all_project_data(project: str) -> Dict[str, List[Dict[str, Any]]]:
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, pdf_path, page, xref, stamp_type, pdf_name, pdf_uuid, pattern_name, stamp_uuid FROM stamps WHERE project=?", (project,))
            stamps_rows = cur.fetchall()
            stamps_dict = {r["id"]: {**dict(r), "fields": {}} for r in stamps_rows}
            
            stamp_ids = list(stamps_dict.keys())
            if not stamp_ids:
                return {"air_outlets": [], "systems": []}
                
            placeholders = ",".join("?" * len(stamp_ids))
            cur.execute(f"SELECT stamp_id, name, value FROM stamp_fields WHERE stamp_id IN ({placeholders})", stamp_ids)
            fields_rows = cur.fetchall()
            
            for r in fields_rows:
                stamps_dict[r["stamp_id"]]["fields"][r["name"]] = r["value"]
                
            air_outlets = []
            systems = []
            
            import re
            for s_id, s_data in stamps_dict.items():
                pat_name = s_data.get("pattern_name") or ""
                m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', pat_name)
                if m:
                    base_pat = m.group(1)
                    auto_num = m.group(2)
                else:
                    base_pat = pat_name
                    auto_num = pat_name
                
                hash_key = "#"
                if not s_data["fields"].get(hash_key):
                    s_data["fields"][hash_key] = auto_num
                    
                res = {
                    "id": s_id,
                    "pdf_path": s_data["pdf_path"],
                    "page": s_data["page"],
                    "xref": s_data["xref"],
                    "pattern_name": base_pat,
                    "stamp_uuid": s_data.get("stamp_uuid") or "",
                    "fields": s_data["fields"]
                }
                if s_data.get("stamp_type") == "system":
                    systems.append(res)
                else:
                    air_outlets.append(res)
                    
            return {
                "air_outlets": air_outlets,
                "systems": systems
            }
        finally:
            conn.close()

def get_pdf_stamps_with_fields(project: str, pdf_path: str, stamp_type: str) -> List[Dict[str, Any]]:
    pdf_path = normalize_db_path(pdf_path)
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, page, xref, pattern_name FROM stamps WHERE project=? AND pdf_path=? AND stamp_type=?",
                (project, pdf_path, stamp_type)
            )
            stamps_rows = cur.fetchall()
            if not stamps_rows:
                return []
                
            stamps_dict = {r["id"]: {**dict(r), "fields": {}} for r in stamps_rows}
            stamp_ids = list(stamps_dict.keys())
            
            placeholders = ",".join("?" * len(stamp_ids))
            cur.execute(f"SELECT stamp_id, name, value FROM stamp_fields WHERE stamp_id IN ({placeholders})", stamp_ids)
            fields_rows = cur.fetchall()
            
            for r in fields_rows:
                stamps_dict[r["stamp_id"]]["fields"][r["name"]] = r["value"]
                
            return list(stamps_dict.values())
        finally:
            conn.close()

def update_stamp_field_bulk(project: str, updates: List[tuple]):
    # updates is a list of (stamp_id, field_name, new_value, new_pattern_name)
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            for stamp_id, field_name, new_value, new_pattern_name in updates:
                # Update stamp_fields
                cur.execute(
                    "UPDATE stamp_fields SET value=? WHERE stamp_id=? AND name=?",
                    (new_value, stamp_id, field_name)
                )
                if cur.rowcount == 0:
                    cur.execute(
                        "INSERT INTO stamp_fields (stamp_id, name, value, type) VALUES (?,?,?,?)",
                        (stamp_id, field_name, new_value, "string")
                    )
                # Update pattern_name
                cur.execute(
                    "UPDATE stamps SET pattern_name=? WHERE id=?",
                    (new_pattern_name, stamp_id)
                )
            conn.commit()
        finally:
            conn.close()

def get_fields_by_type(project: str, stamp_type: str) -> List[str]:
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT f.name
                FROM stamp_fields f
                JOIN stamps s ON s.id = f.stamp_id
                WHERE s.project = ? AND s.stamp_type = ? AND f.name IS NOT NULL
                """,
                (project, stamp_type)
            )
            fields = [row["name"] for row in cur.fetchall()]
            if "#" not in fields:
                fields.insert(0, "#")
            return fields
        finally:
            conn.close()

def get_all_project_data_raw(project: str) -> List[Dict[str, Any]]:
    """Return raw stamp rows for all stamps in a project, used by the sync-from-pdf endpoint."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, stamp_uuid, pdf_path, page, xref, stamp_type, pattern_name FROM stamps WHERE project=?",
                (project,)
            )
            rows = cur.fetchall()
            result = []
            for row in rows:
                result.append({
                    "id": row["id"],
                    "stamp_uuid": row["stamp_uuid"] or "",
                    "pdf_path": row["pdf_path"],
                    "page": row["page"],
                    "xref": row["xref"],
                    "stamp_type": row["stamp_type"] or "air_outlet",
                    "pattern_name": row["pattern_name"] or "",
                })
            return result
        finally:
            conn.close()

def mark_stamp_not_found(project: str, stamp_id: int):
    """Mark a stamp's pattern_name as 'NOT FOUND' in the stamps table."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("UPDATE stamps SET pattern_name=? WHERE id=?", ("NOT FOUND", stamp_id))
            conn.commit()
        finally:
            conn.close()

def sync_update_stamp(
    project: str,
    stamp_id: int,
    new_pdf_path: str,
    new_page: int,
    new_xref: int,
    new_pattern_name,   # str or None — None means "don't overwrite pattern"
    new_stamp_type: str,
    new_number,         # str or None
) -> bool:
    """
    Update a stamp's location and pattern data during a PDF sync.

    - Always updates pdf_path, page, xref to match the current PDF.
    - Updates pattern_name and # field only if new_pattern_name is not None
      (None means the PDF annotation has no real PatternName set — UUID-only name).
    - Updates stamp_type always.
    Returns True if any column was actually changed.
    """
    new_pdf_path = normalize_db_path(new_pdf_path)
    changed = False

    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT pdf_path, page, xref, stamp_type, pattern_name FROM stamps WHERE id=?",
                (stamp_id,)
            )
            row = cur.fetchone()
            if not row:
                return False

            col_updates = []
            col_params  = []

            if normalize_db_path(row["pdf_path"]) != new_pdf_path:
                col_updates.append("pdf_path=?")
                col_params.append(new_pdf_path)
            if row["page"] != new_page:
                col_updates.append("page=?")
                col_params.append(new_page)
            if row["xref"] != new_xref:
                col_updates.append("xref=?")
                col_params.append(new_xref)
            if row["stamp_type"] != new_stamp_type:
                col_updates.append("stamp_type=?")
                col_params.append(new_stamp_type)

            # Only update pattern_name if the PDF has a real name (not UUID-only)
            update_pattern = (
                new_pattern_name is not None
                and row["pattern_name"] != new_pattern_name
            )
            if update_pattern:
                col_updates.append("pattern_name=?")
                col_params.append(new_pattern_name)

            if col_updates:
                col_params.append(stamp_id)
                cur.execute(
                    f"UPDATE stamps SET {', '.join(col_updates)} WHERE id=?",
                    col_params
                )
                changed = True

            # Update # field if we have a real number
            if update_pattern and new_number is not None:
                cur.execute(
                    "UPDATE stamp_fields SET value=? WHERE stamp_id=? AND name=?",
                    (new_number, stamp_id, "#")
                )
                if cur.rowcount == 0:
                    cur.execute(
                        "INSERT INTO stamp_fields (stamp_id, name, value, type) VALUES (?,?,?,?)",
                        (stamp_id, "#", new_number, "string")
                    )
                changed = True

            conn.commit()
            return changed
        finally:
            conn.close()

def delete_stamp_by_id(project: str, stamp_id: int):
    """Hard-delete a stamp row by primary key id (cascades to stamp_fields, stamp_group_assignments)."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM stamps WHERE id=?", (stamp_id,))
            conn.commit()
        finally:
            conn.close()

def update_stamp_location(project: str, pdf_path: str, old_xref: int, new_xref: int, new_page: int):
    pdf_path = normalize_db_path(pdf_path)
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE stamps SET xref=?, page=? WHERE pdf_path=? AND xref=?",
                (new_xref, new_page, pdf_path, old_xref)
            )
            conn.commit()
        finally:
            conn.close()

def get_field_unique_values(project: str, field_name: str) -> List[str]:
    """Return all unique values for a specific field across the project."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT f.value
                FROM stamp_fields f
                JOIN stamps s ON s.id = f.stamp_id
                WHERE s.project = ? AND f.name = ? AND f.value IS NOT NULL AND f.value != ''
                ORDER BY f.value
                """,
                (project, field_name)
            )
            return [row["value"] for row in cur.fetchall()]
        finally:
            conn.close()

def get_all_patterns(project: str) -> List[str]:
    """Return all distinct pattern names across the project."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT pattern_name
                FROM stamps
                WHERE project = ? AND pattern_name IS NOT NULL AND pattern_name != ''
                ORDER BY pattern_name
                """,
                (project,)
            )
            return [row["pattern_name"] for row in cur.fetchall()]
        finally:
            conn.close()

def get_all_system_patterns(project: str) -> List[str]:
    """Return all distinct pattern_name values for system-type stamps only."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT DISTINCT pattern_name
                FROM stamps
                WHERE project = ? AND stamp_type = 'system'
                  AND pattern_name IS NOT NULL AND pattern_name != ''
                ORDER BY pattern_name
                """,
                (project,)
            )
            return [row["pattern_name"] for row in cur.fetchall()]
        finally:
            conn.close()

def get_all_stamps_for_rules(project: str) -> List[Dict[str, Any]]:
    """Return all stamps in a project with their fields, group_id, stamp_type, pattern_name.
    Used by the apply_rules endpoint."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.id, s.pdf_path, s.page, s.xref, s.stamp_type, s.pattern_name,
                       sga.group_id
                FROM stamps s
                LEFT JOIN stamp_group_assignments sga ON sga.stamp_id = s.id
                WHERE s.project = ?
                """,
                (project,)
            )
            stamp_rows = cur.fetchall()
            if not stamp_rows:
                return []

            stamp_ids = [r["id"] for r in stamp_rows]
            stamps = {r["id"]: {**dict(r), "fields": {}} for r in stamp_rows}

            placeholders = ",".join("?" * len(stamp_ids))
            cur.execute(
                f"SELECT stamp_id, name, value FROM stamp_fields WHERE stamp_id IN ({placeholders})",
                stamp_ids
            )
            for r in cur.fetchall():
                stamps[r["stamp_id"]]["fields"][r["name"]] = r["value"]

            return list(stamps.values())
        finally:
            conn.close()

def apply_rule_updates(project: str, updates: List[Dict[str, Any]]) -> int:
    """Apply rule-driven updates to stamps.
    Each update dict has:
      - stamp_id: int
      - pattern_name: str | None   (for shape rules)
      - group_id: int | None        (for color rules; None removes group)
    Returns the count of stamps actually modified."""
    if not updates:
        return 0
    changed = 0
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            for upd in updates:
                sid = upd["stamp_id"]
                if "pattern_name" in upd:
                    cur.execute("UPDATE stamps SET pattern_name=? WHERE id=?",
                                (upd["pattern_name"], sid))
                    changed += 1
                if "group_id" in upd:
                    gid = upd["group_id"]
                    cur.execute("DELETE FROM stamp_group_assignments WHERE stamp_id=?", (sid,))
                    if gid is not None:
                        cur.execute(
                            "INSERT OR REPLACE INTO stamp_group_assignments (stamp_id, group_id) VALUES (?,?)",
                            (sid, gid)
                        )
                    changed += 1
            conn.commit()
            return changed
        finally:
            conn.close()

def find_or_create_color_group(project: str, color: str) -> int:
    """Find a group with the given color or create one. Returns the group id."""
    with _lock:
        conn = _get_connection(project)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM stamp_groups WHERE project=? AND color=? LIMIT 1",
                (project, color)
            )
            row = cur.fetchone()
            if row:
                return row["id"]
            cur.execute(
                "INSERT INTO stamp_groups (project, name, color) VALUES (?,?,?)",
                (project, f"Tag Rule {color}", color)
            )
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()

