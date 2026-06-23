import os
import json
import io
import math
import re
import shutil
import threading
import traceback
import bcrypt
import uuid
try:
    import pythoncom
    import win32com.client
    HAS_WIN32COM = True
except ImportError:
    HAS_WIN32COM = False
from contextlib import redirect_stderr, redirect_stdout
from functools import wraps
from queue import Queue
from flask import (
    Flask, Response, render_template, request, jsonify,
    send_file, abort, stream_with_context, session, redirect, url_for, send_from_directory
)
import fitz  # PyMuPDF
import stamp_db
import doc_renderer

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vpi-change-me-in-production-32chars")

# Base directory where config.json is located
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

PROJECTS_DIR = os.path.join(BASE_DIR, "Projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ── Auth helpers ──────────────────────────────────────────────────────────────
USERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def _ensure_users_file():
    """Create users.json with a default admin account if it doesn't exist."""
    if not os.path.exists(USERS_PATH):
        hashed = bcrypt.hashpw(DEFAULT_PASSWORD.encode(), bcrypt.gensalt()).decode()
        with open(USERS_PATH, "w", encoding="utf-8") as f:
            json.dump([{"username": DEFAULT_USERNAME, "password_hash": hashed}], f, indent=2)


def _load_users():
    _ensure_users_file()
    with open(USERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _verify_password(username, password):
    """Return True if username/password match a record in users.json."""
    for user in _load_users():
        if user.get("username") == username:
            stored = user.get("password_hash", "")
            return bcrypt.checkpw(password.encode(), stored.encode())
    return False


def login_required(f):
    """Decorator: redirect to /login if the user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            from flask import request
            return redirect(url_for("login", next=request.full_path))
        return f(*args, **kwargs)
    return decorated


def api_login_required(f):
    """Decorator: return 401 JSON if the user is not authenticated (for API routes)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


_ensure_users_file()

def load_config():
    if not os.path.exists(CONFIG_PATH):
        # Fallback to current directory if not found in parent
        fallback_path = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r") as f:
                return json.load(f)
        return {"paths": {"input_folder": os.path.join(BASE_DIR, "Sample pdfs")}, "theme": "auto"}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config_data):
    if not os.path.exists(CONFIG_PATH):
        fallback_path = os.path.join(os.path.dirname(__file__), "config.json")
        target_path = fallback_path if os.path.exists(fallback_path) else CONFIG_PATH
    else:
        target_path = CONFIG_PATH
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)


class _QueueWriter:
    def __init__(self, queue_obj):
        self.queue = queue_obj
        self._buffer = ""

    @staticmethod
    def _clean(text):
        return re.sub(r"\x1b\[[0-9;]*m", "", text).rstrip("\r")

    def write(self, text):
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.queue.put({"type": "log", "message": self._clean(line)})
        return len(text)

    def flush(self):
        if self._buffer:
            self.queue.put({"type": "log", "message": self._clean(self._buffer)})
            self._buffer = ""


def stream_task_events(task_fn):
    def generate():
        queue_obj = Queue()
        result_holder = {}

        def worker():
            writer = _QueueWriter(queue_obj)
            try:
                with redirect_stdout(writer), redirect_stderr(writer):
                    result_holder["result"] = task_fn()
            except Exception as e:
                writer.flush()
                for line in traceback.format_exc().splitlines():
                    queue_obj.put({"type": "log", "message": line})
                queue_obj.put({"type": "error", "message": str(e)})
            finally:
                writer.flush()
                queue_obj.put(None)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            item = queue_obj.get()
            if item is None:
                break
            yield json.dumps(item) + "\n"

        if "result" in result_holder:
            yield json.dumps({"type": "result", "data": result_holder["result"]}) + "\n"

    return Response(stream_with_context(generate()), mimetype="application/x-ndjson")


def get_project_name_from_pdf_path(pdf_path):
    project_name = "test"
    normalized = os.path.normpath(pdf_path)
    parts = normalized.split(os.sep)
    for i, part in enumerate(parts):
        if part.lower() == "projects" and i + 1 < len(parts):
            project_name = parts[i + 1]
            break
    return project_name


def get_pdf_undo_backup_path(pdf_path):
    project_name = get_project_name_from_pdf_path(pdf_path)
    pdf_name = os.path.basename(pdf_path)

    if project_name and os.path.normpath(pdf_path).startswith(os.path.normpath(PROJECTS_DIR)):
        undo_dir = os.path.join(PROJECTS_DIR, project_name, ".undo")
        os.makedirs(undo_dir, exist_ok=True)
        return os.path.join(undo_dir, f"{pdf_name}.bak")

    return pdf_path + ".bak"


def create_pdf_undo_backup(pdf_path):
    backup_path = get_pdf_undo_backup_path(pdf_path)
    shutil.copy2(pdf_path, backup_path)
    return backup_path


def restore_pdf_undo_backup(pdf_path):
    backup_path = get_pdf_undo_backup_path(pdf_path)
    if not os.path.exists(backup_path):
        raise FileNotFoundError("No undo snapshot is available for this PDF.")
    shutil.copy2(backup_path, pdf_path)
    return backup_path


def build_project_config(pdf_path, subject_items_module):
    project_name = get_project_name_from_pdf_path(pdf_path)
    cfg = subject_items_module.load_config()
    projects_output_dir = os.path.normpath(os.path.join(PROJECTS_DIR, project_name, "output"))
    os.makedirs(projects_output_dir, exist_ok=True)
    if "paths" not in cfg:
        cfg["paths"] = {}
    cfg["paths"]["output_folder"] = projects_output_dir
    return cfg, project_name


def execute_matching_lines_scan(pdf_path):
    import sys
    if BASE_DIR not in sys.path:
        sys.path.append(BASE_DIR)

    import detect_subject_items as subject_items
    import detect_matching_lines as matching_lines

    cfg, project_name = build_project_config(pdf_path, subject_items)
    targets = cfg.get("targets", [])
    matches, _ = subject_items.scan_pdf(pdf_path, targets)

    if not matches:
        raise ValueError("No matching subject annotations or saved annotations found for this PDF.")

    page_matches = matching_lines.find_matching_lines(pdf_path, matches, cfg)
    output_path = matching_lines.save_layered_matching_pdf(pdf_path, page_matches, cfg)

    if not output_path:
        raise ValueError("No matching lines found to draw.")

    web_path = f"Output/{project_name}/{os.path.basename(output_path)}"
    return {
        "success": True,
        "message": "Layered matching-lines PDF generated successfully.",
        "output_file": web_path
    }


def execute_pattern_scan(pdf_path):
    import sys
    if BASE_DIR not in sys.path:
        sys.path.append(BASE_DIR)

    import detect_subject_items as subject_items
    import detect_patterns as detect_patterns
    import detect_patterns_output as detect_patterns_output

    cfg, project_name = build_project_config(pdf_path, subject_items)
    patterns = detect_patterns.detect_patterns_parallel(pdf_path, cfg)

    if not patterns:
        raise ValueError("No patterns detected.")

    create_pdf_undo_backup(pdf_path)
    output_path = detect_patterns_output.save_pattern_pdf(pdf_path, patterns, cfg, overwrite_input=True)

    if not output_path:
        raise ValueError("Failed to save pattern detection PDF.")

    return {
        "success": True,
        "message": "Pattern detection annotations saved to the current PDF.",
        "output_file": pdf_path
    }


def execute_undo_pattern_scan(pdf_path):
    restore_pdf_undo_backup(pdf_path)
    return {
        "success": True,
        "message": "Last pattern-scan changes were undone for the current PDF.",
        "output_file": pdf_path
    }

def get_input_folder():
    config = load_config()
    return config.get("paths", {}).get("input_folder", os.path.join(BASE_DIR, "Sample pdfs"))

# ── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/"):
            return redirect(next_url)
        return redirect(url_for("home"))

    # Store next url in session on GET requests so it's not lost
    if request.method == "GET":
        next_url = request.args.get("next")
        if next_url:
            session["next_url"] = next_url

    error = None
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            error = "Please fill in both fields."
        elif _verify_password(username, password):
            session["logged_in"] = True
            session["username"] = username
            next_url = request.args.get("next") or session.pop("next_url", None)
            hash_fragment = request.form.get("hash_fragment", "")
            if next_url and next_url.startswith("/"):
                if hash_fragment and hash_fragment.startswith("#"):
                    next_url += hash_fragment
                return redirect(next_url)
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error, username=username)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("logged_in"):
        return redirect(url_for("home"))

    error = None
    username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")
        invite_code = request.form.get("invite_code", "").strip()

        # Validate invite code
        config = load_config()
        active_code = config.get("invite_code", "")
        import time
        created_at = config.get("invite_code_created_at", 0)
        
        if not active_code:
            error = "Registration is currently closed. Ask the administrator for an invitation."
        elif time.time() - created_at > 86400:
            config["invite_code"] = ""
            save_config(config)
            error = "This invitation link has expired (24h limit)."
        elif invite_code != active_code:
            error = "Invalid invitation code."
        # Validate inputs
        elif not username or not password or not confirm or not invite_code:
            error = "Please fill in all fields."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif not re.match(r'^[a-zA-Z0-9_\-]+$', username):
            error = "Username may only contain letters, numbers, - and _."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            # Check uniqueness
            users = _load_users()
            if any(u.get("username") == username for u in users):
                error = f'Username "{username}" is already taken.'
            else:
                # Hash and save
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                users.append({"username": username, "password_hash": hashed})
                try:
                    # Clear used invite code
                    config["invite_code"] = ""
                    save_config(config)
                    
                    with open(USERS_PATH, "w", encoding="utf-8") as f:
                        json.dump(users, f, indent=2)
                    return redirect(url_for("register") + "?created=1")
                except Exception as e:
                    error = f"Failed to save account: {e}"

    return render_template("register.html", error=error, username=username)


@app.route("/home")
@login_required
def home():
    return render_template("home.html", current_user=session.get("username", "user"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")

@app.route("/api/pdfs", methods=["GET"])
@api_login_required
def list_pdfs():
    input_folder = get_input_folder()
    if not os.path.exists(input_folder):
        return jsonify({"error": f"Folder not found: {input_folder}"}), 404
        
    pdfs = []
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, input_folder)
                pdfs.append({
                    "name": file,
                    "path": rel_path.replace("\\", "/") # Normalize path for web
                })
    return jsonify(pdfs)

def get_pdf_path(filename):
    if os.path.isabs(filename):
        normalized_path = os.path.normpath(filename)
        projects_dir = os.path.normpath(PROJECTS_DIR)
        input_folder = os.path.normpath(get_input_folder())
        norm_path_lower = normalized_path.lower()
        if norm_path_lower.startswith(projects_dir.lower()) or norm_path_lower.startswith(input_folder.lower()):
            return normalized_path
        return None

    if filename.startswith("Projects/"):
        # Resolve relative to BASE_DIR and ensure it is inside PROJECTS_DIR
        normalized_path = os.path.normpath(os.path.join(BASE_DIR, filename))
        if not normalized_path.startswith(PROJECTS_DIR):
            return None
        return normalized_path
    elif filename.lower().startswith("output/"):
        rel_path = filename[len("output/"):]
        parts = os.path.normpath(rel_path).split(os.sep)
        if len(parts) >= 2:
            project_name = parts[0]
            rest = os.sep.join(parts[1:])
            output_folder = os.path.normpath(os.path.join(PROJECTS_DIR, project_name, "output"))
            normalized_path = os.path.normpath(os.path.join(output_folder, rest))
        else:
            output_folder = os.path.normpath(os.path.join(PROJECTS_DIR, "output"))
            normalized_path = os.path.normpath(os.path.join(output_folder, rel_path))
            
        os.makedirs(output_folder, exist_ok=True)
        if not normalized_path.startswith(output_folder):
            return None
        return normalized_path
    else:
        input_folder = get_input_folder()
        # Ensure no path traversal
        normalized_path = os.path.normpath(os.path.join(input_folder, filename))
        if not normalized_path.startswith(input_folder):
            return None
        return normalized_path

@app.route("/api/pdf/<path:filename>/info", methods=["GET"])
@api_login_required
def pdf_info(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404
        
    try:
        doc = fitz.open(pdf_path)
        info = {
            "page_count": len(doc),
            "metadata": doc.metadata
        }
        doc.close()
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/raw", methods=["GET"])
@api_login_required
def get_raw_pdf(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        abort(404, description="File not found")
        
    return send_file(pdf_path, mimetype="application/pdf")

@app.route("/api/pdf/<path:filename>/page/<int:page_num>/image", methods=["GET"])
@api_login_required
def get_page_image(filename, page_num):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        abort(404, description="File not found")
        
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            abort(404, description="Page not found")
            
        page = doc[page_num - 1]
        
        # Determine scale and optional clip region from query params
        scale_param = request.args.get("scale", "2")
        clip_param = request.args.get("clip")
        
        clip_rect = None
        w, h = page.rect.width, page.rect.height
        
        if clip_param:
            try:
                cx0, cy0, cw, ch = map(float, clip_param.split(","))
                # Intersect clip with page rect to be safe
                clip_rect = fitz.Rect(cx0, cy0, cx0 + cw, cy0 + ch) & page.rect
                if not clip_rect.is_empty:
                    w, h = clip_rect.width, clip_rect.height
                else:
                    clip_rect = None
            except Exception:
                clip_rect = None
                
        try:
            scale_val = float(scale_param)
            scale_val = max(scale_val, 1.0)
            
            # Cap limits to ensure the browser can allocate and render the image:
            # - Max width or height: 16,384 pixels (WebGL/GPU texture limit)
            # - Max total area: 250,000,000 pixels (Chrome canvas/image limit)
            MAX_DIMENSION = 16384.0
            MAX_PIXELS = 250_000_000
            
            area = w * h
            if area > 0:
                # Limit by max dimension
                scale_limit_dim = MAX_DIMENSION / max(w, h)
                # Limit by max area
                scale_limit_area = math.sqrt(MAX_PIXELS / area)
                
                # Combine limits, ensuring max_scale is at least 3.0 (legibility) and at most 48.0
                max_scale = min(max(min(scale_limit_dim, scale_limit_area), 3.0), 48.0)
            else:
                max_scale = 8.0
                
            scale_val = min(scale_val, max_scale)
        except ValueError:
            scale_val = 2.0
            
        # Render at requested scale
        mat = fitz.Matrix(scale_val, scale_val)
        pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
        
        # Convert to bytes
        img_data = pix.tobytes("jpeg")
        doc.close()
        
        return send_file(
            io.BytesIO(img_data),
            mimetype="image/jpeg",
            as_attachment=False,
            download_name=f"page_{page_num}.jpg"
        )
    except Exception as e:
        abort(500, description=str(e))

@app.route("/api/pdf/<path:filename>/page/<int:page_num>/svg", methods=["GET"])
@api_login_required
def get_page_svg(filename, page_num):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        abort(404, description="File not found")
        
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            abort(404, description="Page not found")
            
        page = doc[page_num - 1]
        svg_data = page.get_svg_image()
        doc.close()
        
        return send_file(
            io.BytesIO(svg_data.encode("utf-8")),
            mimetype="image/svg+xml",
            as_attachment=False,
            download_name=f"page_{page_num}.svg"
        )
    except Exception as e:
        abort(500, description=str(e))

def format_color(color_tuple):
    if not color_tuple:
        return None
    if len(color_tuple) == 3:
        r = int(color_tuple[0] * 255)
        g = int(color_tuple[1] * 255)
        b = int(color_tuple[2] * 255)
        return f"#{r:02x}{g:02x}{b:02x}"
    return None

def rgb_array(color_tuple):
    if not color_tuple:
        return None
    if len(color_tuple) == 3:
        return [color_tuple[0], color_tuple[1], color_tuple[2]]
    return None

@app.route("/api/pdf/<path:filename>/page/<int:page_num>/drawings", methods=["GET"])
@api_login_required
def get_page_drawings(filename, page_num):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404
    cache_dir = pdf_path + ".cache"
    cache_file = os.path.join(cache_dir, f"drawings_page_{page_num}.json")
    
    if os.path.exists(cache_file):
        from flask import send_file
        return send_file(cache_file, mimetype="application/json")
        
    try:
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            return jsonify({"error": "Page not found"}), 404
            
        page = doc[page_num - 1]
        drawings = page.get_drawings()
        
        serialized_drawings = []
        
        # Add page rect so frontend knows the coordinate system bounds
        page_bounds = {"width": page.rect.width, "height": page.rect.height}
        
        # Get rotation matrix to transform drawings coordinates to match the rotated page
        rot_matrix = page.rotation_matrix
        
        for d_idx, drawing in enumerate(drawings):
            line_weight = drawing.get("width")
            if line_weight is None:
                line_weight = 1.0
            stroke_color_tuple = drawing.get("color")
            fill_color_tuple = drawing.get("fill")
            
            color_hex = format_color(stroke_color_tuple)
            color_rgb = rgb_array(stroke_color_tuple)
            
            fill_color_hex = format_color(fill_color_tuple)
            
            for i_idx, item in enumerate(drawing.get("items", [])):
                item_type = item[0]
                
                # Each primitive is extracted individually as requested
                if item_type == "l":
                    p1, p2 = item[1] * rot_matrix, item[2] * rot_matrix
                    length = math.hypot(p2.x - p1.x, p2.y - p1.y)
                    serialized_drawings.append({
                        "id": f"{d_idx}_{i_idx}",
                        "type": "Line",
                        "start": [p1.x, p1.y],
                        "end": [p2.x, p2.y],
                        "length": round(length, 4),
                        "thickness": round(line_weight, 4),
                        "color": color_rgb,
                        "color_hex": color_hex,
                        "fill_color_hex": fill_color_hex
                    })
                elif item_type == "re":
                    rect = item[1] * rot_matrix
                    width = rect.width
                    height = rect.height
                    length = width * 2 + height * 2 # Perimeter
                    serialized_drawings.append({
                        "id": f"{d_idx}_{i_idx}",
                        "type": "Rect",
                        "x": rect.x0,
                        "y": rect.y0,
                        "width": width,
                        "height": height,
                        "length": round(length, 4),
                        "thickness": round(line_weight, 4),
                        "color": color_rgb,
                        "color_hex": color_hex,
                        "fill_color_hex": fill_color_hex
                    })
                elif item_type == "qu":
                    quad = item[1] * rot_matrix
                    ul, ur, ll, lr = quad.ul, quad.ur, quad.ll, quad.lr
                    d1 = math.hypot(ur.x - ul.x, ur.y - ul.y)
                    d2 = math.hypot(lr.x - ur.x, lr.y - ur.y)
                    d3 = math.hypot(ll.x - lr.x, ll.y - lr.y)
                    d4 = math.hypot(ul.x - ll.x, ul.y - ll.y)
                    length = d1 + d2 + d3 + d4
                    serialized_drawings.append({
                        "id": f"{d_idx}_{i_idx}",
                        "type": "Polygon",
                        "points": [
                            [ul.x, ul.y],
                            [ur.x, ur.y],
                            [lr.x, lr.y],
                            [ll.x, ll.y]
                        ],
                        "length": round(length, 4),
                        "thickness": round(line_weight, 4),
                        "color": color_rgb,
                        "color_hex": color_hex,
                        "fill_color_hex": fill_color_hex
                    })
                elif item_type == "c":
                    p1 = item[1] * rot_matrix
                    p2 = item[2] * rot_matrix
                    p3 = item[3] * rot_matrix
                    p4 = item[4] * rot_matrix
                    # Approximate length of bezier curve (sum of segments)
                    d1 = math.hypot(p2.x - p1.x, p2.y - p1.y)
                    d2 = math.hypot(p3.x - p2.x, p3.y - p2.y)
                    d3 = math.hypot(p4.x - p3.x, p4.y - p3.y)
                    approx_length = d1 + d2 + d3
                    
                    serialized_drawings.append({
                        "id": f"{d_idx}_{i_idx}",
                        "type": "Arc/Curve",
                        "points": [
                            [p1.x, p1.y],
                            [p2.x, p2.y],
                            [p3.x, p3.y],
                            [p4.x, p4.y]
                        ],
                        "length": round(approx_length, 4),
                        "thickness": round(line_weight, 4),
                        "color": color_rgb,
                        "color_hex": color_hex,
                        "fill_color_hex": fill_color_hex
                    })
                # 'v' and 'y' are also bezier curves but with implicit control points
                # PyMuPDF 'items' usually normalizes these to 'c', but just in case:
                elif item_type in ("v", "y"):
                    # For raw data extraction, we can just log these as Arc/Curve
                    pass
        
        # Extract hyperlinks
        links = page.get_links()
        serialized_links = []
        for link in links:
            if link.get("kind") == fitz.LINK_URI and link.get("uri"):
                rect = link.get("from") # already in rotated page coordinates
                serialized_links.append({
                    "uri": link.get("uri"),
                    "x": rect.x0,
                    "y": rect.y0,
                    "width": rect.width,
                    "height": rect.height
                })
        
        doc.close()
        
        response_data = {
            "page_bounds": page_bounds,
            "drawings": serialized_drawings,
            "links": serialized_links
        }
        
        os.makedirs(cache_dir, exist_ok=True)
        temp_cache_file = os.path.join(cache_dir, f"drawings_page_{page_num}_{uuid.uuid4().hex}.tmp")
        with open(temp_cache_file, "w", encoding="utf-8") as f:
            json.dump(response_data, f)
        os.replace(temp_cache_file, cache_file)
            
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects", methods=["GET"])
@api_login_required
def list_projects():
    if not os.path.exists(PROJECTS_DIR):
        os.makedirs(PROJECTS_DIR, exist_ok=True)
    
    projects = []
    try:
        for entry in os.scandir(PROJECTS_DIR):
            if entry.is_dir():
                proj_path = entry.path
                max_mtime = entry.stat().st_mtime
                try:
                    for root, dirs, files in os.walk(proj_path):
                        for d in dirs:
                            try:
                                m = os.path.getmtime(os.path.join(root, d))
                                if m > max_mtime:
                                    max_mtime = m
                            except OSError:
                                pass
                        for f in files:
                            try:
                                m = os.path.getmtime(os.path.join(root, f))
                                if m > max_mtime:
                                    max_mtime = m
                            except OSError:
                                pass
                except Exception:
                    pass

                import datetime
                dt = datetime.datetime.fromtimestamp(max_mtime, datetime.timezone.utc)
                modified_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                c_dt = datetime.datetime.fromtimestamp(entry.stat().st_ctime, datetime.timezone.utc)
                created_str = c_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Read project metadata if it exists
                address = ""
                info_path = os.path.join(proj_path, "project_meta.json")
                if os.path.exists(info_path):
                    try:
                        with open(info_path, "r", encoding="utf-8") as f:
                            meta = json.load(f)
                            address = meta.get("address", "")
                    except Exception:
                        pass

                projects.append({
                    "name": entry.name,
                    "path": entry.name,
                    "modified": modified_str,
                    "created": created_str,
                    "address": address
                })
        projects.sort(key=lambda p: p["name"].lower())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(projects)

@app.route("/api/projects", methods=["POST"])
@api_login_required
def create_project():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    address = data.get("address", "").strip()
    if not name:
        return jsonify({"error": "Project name is required"}), 400
        
    # Sanitize project name
    sanitized_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name).strip()
    if not sanitized_name:
        return jsonify({"error": "Invalid project name"}), 400
        
    proj_path = os.path.join(PROJECTS_DIR, sanitized_name)
    pdfs_path = os.path.join(proj_path, "pdfs")
    
    try:
        os.makedirs(pdfs_path, exist_ok=True)
        
        # Save address if provided
        info_path = os.path.join(proj_path, "project_meta.json")
        with open(info_path, "w", encoding="utf-8") as f:
            json.dump({"address": address}, f, ensure_ascii=False)
            
        return jsonify({"success": True, "name": sanitized_name, "address": address}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/fields/<stamp_type>", methods=["GET"])
@api_login_required
def get_stamp_fields(project_name, stamp_type):
    try:
        fields = stamp_db.get_fields_by_type(project_name, stamp_type)
        return jsonify(fields)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/renumber_stamps", methods=["POST"])
@api_login_required
def renumber_stamps(project_name):
    data = request.get_json() or {}
    pdf_path = data.get("pdf_path")
    stamp_type = data.get("stamp_type")
    group_field = data.get("group_field", "")
    field_name = data.get("field_name", "#")
    
    if not pdf_path or not stamp_type:
        return jsonify({"error": "Missing parameters"}), 400
        
    try:
        import sys
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
        
        import fitz
        from detect_patterns_output import cluster_y_coordinates
        
        # Get full PDF path
        full_pdf_path = get_pdf_path(pdf_path)
        if not full_pdf_path or not os.path.exists(full_pdf_path):
             return jsonify({"error": "PDF not found"}), 404
             
        # Get stamps from DB using the resolved path
        stamps = stamp_db.get_pdf_stamps_with_fields(project_name, full_pdf_path, stamp_type)
        if not stamps:
            return jsonify({"success": True, "message": "No stamps found to renumber."})

        doc = fitz.open(full_pdf_path)
        
        # Attach bounding boxes to stamps
        valid_stamps = []
        for s in stamps:
            # Only include stamps containing the target field (or '#' which is default)
            if field_name == "#" or field_name in s.get("fields", {}):
                xref = s["xref"]
                page_num = s["page"]
                try:
                    page = doc[page_num - 1]
                    annot = page.load_annot(xref)
                    if annot:
                        rect = annot.rect
                        s["bbox"] = [rect.x0, rect.y0, rect.x1, rect.y1]
                        valid_stamps.append(s)
                except Exception:
                    pass
        
        # Group stamps by the chosen group_field value
        from collections import defaultdict
        grouped_stamps = defaultdict(list)
        for s in valid_stamps:
            if group_field:
                val = s.get("fields", {}).get(group_field, "")
                grouped_stamps[val].append(s)
            else:
                grouped_stamps[""].append(s)
                
        updates = []
        for g_val, g_stamps in grouped_stamps.items():
            # Group by page within this group
            by_page = defaultdict(list)
            for s in g_stamps:
                by_page[s["page"]].append(s)
                
            seq_num = 0
            for page_num in sorted(by_page.keys()):
                page_stamps = by_page[page_num]
                sorted_stamps = cluster_y_coordinates(page_stamps)
                for s in sorted_stamps:
                    seq_num += 1
                    
                    # Do not include the group value in the sequence number
                    new_hash_value = str(seq_num)
                    
                    pat_name = s.get("pattern_name") or ""
                    import re
                    m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', pat_name)
                    if m:
                        base_pat = m.group(1)
                    else:
                        base_pat = pat_name
                        
                    new_pattern_name = f"{base_pat}_{new_hash_value}" if base_pat else new_hash_value
                    
                    updates.append((s["id"], field_name, new_hash_value, new_pattern_name))
                    
                    # Update the PDF annotation
                    try:
                        page = doc[s["page"] - 1]
                        annot = page.load_annot(s["xref"])
                        if annot:
                            # Update raw NM key (annotation name) and PatternName if present
                            doc.xref_set_key(annot.xref, "NM", f"({new_pattern_name})")
                            p_val = doc.xref_get_key(annot.xref, "PatternName")
                            if p_val and p_val[0] != "null":
                                doc.xref_set_key(annot.xref, "PatternName", f"({new_pattern_name})")
                            
                            info = annot.info
                            info["content"] = str(new_hash_value)
                            annot.set_info(info)
                            annot.update()
                    except Exception as e:
                        print("Failed to update PDF annotation in renumber_stamps:", e)
                        
        # Save changes to the PDF
        try:
            doc.saveIncr()
        except Exception as e:
            print("Failed to save PDF incrementally in renumber_stamps:", e)
        finally:
            doc.close()
                
        # Bulk update database
        stamp_db.update_stamp_field_bulk(project_name, updates)
        
        return jsonify({"success": True, "renumbered": len(updates)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>", methods=["PATCH"])
@api_login_required
def update_project(project_name):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_path = os.path.join(PROJECTS_DIR, sanitized_proj)

    if not os.path.exists(proj_path):
        return jsonify({"error": "Project not found"}), 404

    # Safety: must be directly inside PROJECTS_DIR
    normalized = os.path.normpath(proj_path)
    if not normalized.startswith(os.path.normpath(PROJECTS_DIR)) or \
       normalized == os.path.normpath(PROJECTS_DIR):
        return jsonify({"error": "Invalid project path"}), 400

    data = request.get_json() or {}
    new_name = data.get("new_name" if "new_name" in data else "name", "").strip()
    new_address = data.get("address", None)

    info_path = os.path.join(proj_path, "project_meta.json")
    meta = {}
    if os.path.exists(info_path):
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

    if new_address is not None:
        meta["address"] = new_address.strip()
        try:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False)
        except Exception as e:
            return jsonify({"error": f"Failed to save metadata: {str(e)}"}), 500

    if new_name and new_name != sanitized_proj:
        sanitized_new_name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', new_name).strip()
        if not sanitized_new_name:
            return jsonify({"error": "Invalid new project name"}), 400
        
        new_proj_path = os.path.join(PROJECTS_DIR, sanitized_new_name)
        if os.path.exists(new_proj_path):
            return jsonify({"error": "A project with that name already exists"}), 409
            
        normalized_new = os.path.normpath(new_proj_path)
        if not normalized_new.startswith(os.path.normpath(PROJECTS_DIR)) or \
           normalized_new == os.path.normpath(PROJECTS_DIR):
            return jsonify({"error": "Invalid target project path"}), 400

        try:
            os.rename(proj_path, new_proj_path)
            sanitized_proj = sanitized_new_name
        except Exception as e:
            return jsonify({"error": f"Failed to rename project folder: {str(e)}"}), 500

    return jsonify({"success": True, "name": sanitized_proj, "address": meta.get("address", "")})

@app.route("/api/projects/<project_name>", methods=["DELETE"])
@api_login_required
def delete_project(project_name):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_path = os.path.join(PROJECTS_DIR, sanitized_proj)

    if not os.path.exists(proj_path):
        return jsonify({"error": "Project not found"}), 404

    # Safety: must be directly inside PROJECTS_DIR
    normalized = os.path.normpath(proj_path)
    if not normalized.startswith(os.path.normpath(PROJECTS_DIR)) or \
       normalized == os.path.normpath(PROJECTS_DIR):
        return jsonify({"error": "Invalid project path"}), 400

    try:
        shutil.rmtree(proj_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects/<project_name>/pdf/<path:filename>", methods=["DELETE"])
@api_login_required
def delete_project_pdf(project_name, filename):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    # Safety: ensure it is inside the project's pdfs folder
    proj_pdfs_dir = os.path.normpath(os.path.join(PROJECTS_DIR, sanitized_proj, "pdfs"))
    if not os.path.normpath(pdf_path).startswith(proj_pdfs_dir):
        return jsonify({"error": "Unauthorized path access"}), 403

    try:
        # Delete database entries associated with this PDF
        stamp_db.delete_all_pdf_stamps(sanitized_proj, pdf_path)
        
        # Delete backup/undo file if exists
        backup_path = get_pdf_undo_backup_path(pdf_path)
        if os.path.exists(backup_path):
            os.remove(backup_path)

        # Delete patterns JSON file if exists
        pdf_name = os.path.basename(pdf_path)
        patterns_dir = get_project_patterns_dir(sanitized_proj)
        pattern_file = os.path.join(patterns_dir, f"{pdf_name}_patterns.json")
        if os.path.exists(pattern_file):
            os.remove(pattern_file)

        # Delete the actual PDF file
        os.remove(pdf_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/projects/<project_name>/pdfs", methods=["GET"])
@api_login_required
def list_project_pdfs(project_name):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_pdfs_dir = os.path.join(PROJECTS_DIR, sanitized_proj, "pdfs")
    
    if not os.path.exists(proj_pdfs_dir):
        return jsonify({"error": "Project not found"}), 404
        
    pdfs = []
    try:
        for entry in os.scandir(proj_pdfs_dir):
            if entry.is_file() and entry.name.lower().endswith(".pdf"):
                rel_path = f"Projects/{sanitized_proj}/pdfs/{entry.name}"
                pdfs.append({
                    "name": entry.name,
                    "path": rel_path
                })
        pdfs.sort(key=lambda p: p["name"].lower())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(pdfs)

@app.route("/api/config", methods=["GET"])
@api_login_required
def get_config():
    try:
        return jsonify(load_config())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/config", methods=["POST"])
@api_login_required
def update_config():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        cfg = load_config()
        if "theme" in data:
            cfg["theme"] = data["theme"]
        if "auto_scroll_speed" in data:
            cfg["auto_scroll_speed"] = float(data["auto_scroll_speed"])
            
        save_config(cfg)
        return jsonify({"success": True, "theme": cfg.get("theme")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/upload", methods=["POST"])
@api_login_required
def upload_project_pdf(project_name):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_pdfs_dir = os.path.join(PROJECTS_DIR, sanitized_proj, "pdfs")
    
    if not os.path.exists(proj_pdfs_dir):
        return jsonify({"error": "Project not found"}), 404
        
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400
        
    if file and file.filename.lower().endswith('.pdf'):
        filename = file.filename
        name, ext = os.path.splitext(os.path.basename(filename))
        name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name).strip()
        name = name[:100]
        safe_filename = name + ext.lower()
        
        target_path = os.path.join(proj_pdfs_dir, safe_filename)
        try:
            file.save(target_path)
            rel_path = f"Projects/{sanitized_proj}/pdfs/{safe_filename}"
            return jsonify({
                "success": True,
                "name": safe_filename,
                "path": rel_path
            }), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Only PDF files are allowed"}), 400

@app.route("/api/projects/<project_name>/annotations", methods=["GET"])
@api_login_required
def list_annotations(project_name):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_dir = os.path.join(PROJECTS_DIR, sanitized_proj)
    if not os.path.exists(proj_dir):
        return jsonify({"error": "Project not found"}), 404
        
    ann_file = os.path.join(proj_dir, "annotations.json")
    if not os.path.exists(ann_file):
        return jsonify([])
        
    try:
        with open(ann_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/annotations", methods=["POST"])
@api_login_required
def add_annotation(project_name):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_dir = os.path.join(PROJECTS_DIR, sanitized_proj)
    if not os.path.exists(proj_dir):
        return jsonify({"error": "Project not found"}), 404
        
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    item_type = data.get("type", "").strip()
    pdf_path = data.get("pdf_path", "").strip()
    page_num = data.get("page_num")
    vectors = data.get("vectors", [])
    
    if not name or not item_type or not pdf_path or page_num is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    ann_file = os.path.join(proj_dir, "annotations.json")
    annotations = []
    if os.path.exists(ann_file):
        try:
            with open(ann_file, "r", encoding="utf-8") as f:
                annotations = json.load(f)
        except Exception:
            annotations = []
            
    import time
    new_id = f"annot_{int(time.time() * 1000)}"
    new_ann = {
        "id": new_id,
        "name": name,
        "type": item_type,
        "pdf_path": pdf_path,
        "page_num": int(page_num),
        "vectors": vectors,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    annotations.append(new_ann)
    
    try:
        with open(ann_file, "w", encoding="utf-8") as f:
            json.dump(annotations, f, indent=2, ensure_ascii=False)
        return jsonify({"success": True, "id": new_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/run-matching-lines", methods=["POST"])
@api_login_required
def run_matching_lines(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    try:
        return jsonify(execute_matching_lines_scan(pdf_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/run-patterns", methods=["POST"])
@api_login_required
def run_patterns(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    try:
        return jsonify(execute_pattern_scan(pdf_path))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/pdf/<path:filename>/run-patterns-stream", methods=["POST"])
@api_login_required
def run_patterns_stream(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    return stream_task_events(lambda: execute_pattern_scan(pdf_path))


@app.route("/api/pdf/<path:filename>/undo-pattern-scan", methods=["POST"])
@api_login_required
def undo_pattern_scan(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    try:
        return jsonify(execute_undo_pattern_scan(pdf_path))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def format_display_name(name: str) -> str:
    if not name:
        return name
    chars = list(name)
    n = len(chars)
    i = n - 1
    while i >= 0 and chars[i].isspace():
        i -= 1
    has_digit = False
    while i >= 0 and chars[i].isdigit():
        has_digit = True
        i -= 1
    if has_digit and i >= 0 and chars[i] == '_':
        chars[i] = ' '
        return "".join(chars)
    return name

@app.route("/api/pdf/<path:filename>/stamps", methods=["GET"])
@api_login_required
def get_pdf_stamps(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404
        
    project = filename.split("/")[1] if filename.startswith("Projects/") else (filename.split("/")[1] if filename.lower().startswith("output/") else "default")
    
    stamps = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            rot_matrix = page.rotation_matrix
            for annot in page.annots() or []:
                if annot.type[1] == "Stamp":
                    rect = annot.rect * rot_matrix
                    def _read_str_key(xref_id, key):
                        val_tuple = page.parent.xref_get_key(xref_id, key)
                        if val_tuple[0] == "string":
                            v = val_tuple[1]
                            return v[1:-1] if (v.startswith("(") and v.endswith(")")) else v
                        return ""
                        
                    # ── Read UUID ────────────────────────────────────────
                    uuid_val = page.parent.xref_get_key(annot.xref, "StampID")
                    stamp_uuid = ""
                    if uuid_val[0] == "string":
                        v = uuid_val[1]
                        stamp_uuid = v[1:-1] if (v.startswith("(") and v.endswith(")")) else v
                    if not stamp_uuid:
                        name_val = page.parent.xref_get_key(annot.xref, "Name")
                        if name_val[0] == "name":
                            stamp_uuid = name_val[1].lstrip("/")
                    if not stamp_uuid:
                        n = annot.info.get("name") or ""
                        if re.match(r'^[0-9a-f\-]{32,36}$', n.strip(), re.IGNORECASE):
                            stamp_uuid = n.strip()
                    if not stamp_uuid:
                        stamp_uuid = annot.info.get("id") or ""
                        
                    # ── Read PatternName ─────────────────────────────────
                    pattern_name_key = _read_str_key(annot.xref, "PatternName")
                    nm_key           = _read_str_key(annot.xref, "NM")
                    annot_id         = annot.info.get("id") or ""
                    
                    raw_name = pattern_name_key or nm_key or annot_id
                    
                    display_pattern_name = raw_name
                    if not display_pattern_name and annot_id and not annot_id.startswith("fitz-"):
                        display_pattern_name = annot_id
                        
                    formatted_name = format_display_name(display_pattern_name)
                    
                    # If formatted name looks like a bare UUID, it's not a real pattern name
                    if re.match(r'^[0-9a-f\-]{32,36}$', formatted_name.strip(), re.IGNORECASE):
                        formatted_name = ""
                    stamp_data = {
                        "xref": annot.xref,
                        "page_num": page_num + 1,
                        "rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                        "subject": annot.info.get("subject") or "Stamp",
                        "title": annot.info.get("title") or "User",
                        "name": annot.info.get("name") or formatted_name or annot_id or "",
                        "stamp_uuid": stamp_uuid,
                        "pattern_name": formatted_name,
                        "content": annot.info.get("content") or "",
                        "group_color": None
                    }
                    try:
                        subject = (annot.info.get("subject") or "").lower().strip()
                        type_val = "system" if "system" in subject else "air_outlet"
                        stamp_id = stamp_db.get_or_create_stamp(project, pdf_path, page_num + 1, annot.xref, stamp_type=type_val, pattern_name=formatted_name, stamp_uuid=stamp_uuid)
                        meta = stamp_db.get_stamp_metadata(project, stamp_id)
                        if meta.get("group"):
                            stamp_data["group_color"] = meta["group"]["color"]
                        if meta.get("full_pattern_name"):
                            stamp_data["pattern_name"] = meta["full_pattern_name"]
                            # Intentionally NOT overriding stamp_data["name"] so the original tag data/name is preserved.
                        if meta.get("fields"):
                            stamp_data["fields"] = meta["fields"]
                    except Exception:
                        pass
                    stamps.append(stamp_data)
        doc.close()
        return jsonify(stamps)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/stamps/<int:xref>", methods=["DELETE", "POST"])
@api_login_required
def delete_stamp(filename, xref):
    force_delete = request.args.get('force', '').lower() in ['true', '1', 'yes']
    pdf_path = get_pdf_path(filename)
    
    if not pdf_path:
        return jsonify({"error": "Invalid file path"}), 404
        
    if not os.path.exists(pdf_path):
        if force_delete:
            try:
                stamp_db.delete_stamp_record(get_project_name_from_pdf_path(pdf_path), pdf_path, xref)
            except Exception as e:
                return jsonify({"error": f"Failed to force-delete from database: {str(e)}"}), 500
            return jsonify({"success": True, "message": "File not found, but database record force-deleted."})
        return jsonify({"error": "File not found"}), 404
        
    try:
        doc = fitz.open(pdf_path)
        found = False
        for page in doc:
            for annot in page.annots() or []:
                if annot.xref == xref:
                    stamp_id = annot.info.get("name")
                    stamp_uuid_val = page.parent.xref_get_key(annot.xref, "StampID")
                    stamp_uuid = ""
                    if stamp_uuid_val[0] == "string":
                        val = stamp_uuid_val[1]
                        if val.startswith("(") and val.endswith(")"):
                            stamp_uuid = val[1:-1]
                        else:
                            stamp_uuid = val
                            
                    links_to_delete = []
                    for link in page.get_links():
                        uri = link.get("uri", "")
                        if stamp_id and f"#stamp-{stamp_id}" in uri:
                            links_to_delete.append(link)
                        elif stamp_uuid and f"#stamp-{stamp_uuid}" in uri:
                            links_to_delete.append(link)
                        elif link.get("from") and (link["from"] & annot.rect).get_area() / annot.rect.get_area() > 0.8:
                            if "tabsoftwear.salcerandco.com" in uri or "#stamp-" in uri:
                                links_to_delete.append(link)
                    for link in links_to_delete:
                        try:
                            page.delete_link(link)
                        except Exception:
                            pass
                            
                    page.delete_annot(annot)
                    found = True
                    break
            if found:
                break
                
        if not found:
            doc.close()
            if force_delete:
                try:
                    stamp_db.delete_stamp_record(get_project_name_from_pdf_path(pdf_path), pdf_path, xref)
                except Exception:
                    pass
                return jsonify({"success": True, "message": f"Stamp annotation not found in PDF, but database record deleted."})
            return jsonify({"error": f"Stamp annotation with xref {xref} not found"}), 404
            
        # Try to save incrementally first to avoid WinError 5 (file lock) on Windows
        try:
            doc.saveIncr()
            doc.close()
        except Exception:
            # Fallback to saving to a temp file and replacing if incremental save is not possible
            tmp_path = pdf_path + ".tmp"
            doc.save(tmp_path, deflate=True)
            doc.close()
            os.replace(tmp_path, pdf_path)
        
        # Clean up database record
        try:
            stamp_db.delete_stamp_record(get_project_name_from_pdf_path(pdf_path), pdf_path, xref)
        except Exception:
            pass

        return jsonify({"success": True, "message": f"Stamp with xref {xref} deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/stamps/bulk-delete", methods=["POST"])
@api_login_required
def bulk_delete_stamps(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    data = request.json or {}
    xrefs_to_delete = data.get("xrefs", [])
    if not isinstance(xrefs_to_delete, list):
        return jsonify({"error": "xrefs must be a list"}), 400

    xrefs_to_delete = set(int(x) for x in xrefs_to_delete)
    
    try:
        doc = fitz.open(pdf_path)
        deleted_count = 0
        
        for page in doc:
            for annot in page.annots() or []:
                if annot.xref in xrefs_to_delete:
                    stamp_id = annot.info.get("name")
                    stamp_uuid_val = page.parent.xref_get_key(annot.xref, "StampID")
                    stamp_uuid = ""
                    if stamp_uuid_val[0] == "string":
                        val = stamp_uuid_val[1]
                        if val.startswith("(") and val.endswith(")"):
                            stamp_uuid = val[1:-1]
                        else:
                            stamp_uuid = val
                            
                    links_to_delete = []
                    for link in page.get_links():
                        uri = link.get("uri", "")
                        if stamp_id and f"#stamp-{stamp_id}" in uri:
                            links_to_delete.append(link)
                        elif stamp_uuid and f"#stamp-{stamp_uuid}" in uri:
                            links_to_delete.append(link)
                        elif link.get("from") and (link["from"] & annot.rect).get_area() / annot.rect.get_area() > 0.8:
                            if "tabsoftwear.salcerandco.com" in uri or "#stamp-" in uri:
                                links_to_delete.append(link)
                    for link in links_to_delete:
                        try:
                            page.delete_link(link)
                        except Exception:
                            pass
                            
                    page.delete_annot(annot)
                    deleted_count += 1
                    
        # Try to save incrementally first to avoid WinError 5 (file lock) on Windows
        try:
            doc.saveIncr()
            doc.close()
        except Exception:
            # Fallback to saving to a temp file and replacing if incremental save is not possible
            tmp_path = pdf_path + ".tmp"
            doc.save(tmp_path, deflate=True)
            doc.close()
            os.replace(tmp_path, pdf_path)
        
        # Clean up database records
        project_name = get_project_name_from_pdf_path(pdf_path)
        import stamp_db
        for xref in xrefs_to_delete:
            try:
                stamp_db.delete_stamp_record(project_name, pdf_path, xref)
            except Exception:
                pass

        return jsonify({"success": True, "message": f"{deleted_count} stamp(s) deleted successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/stamps/<int:xref>/move", methods=["PATCH"])
@api_login_required
def move_stamp(filename, xref):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    data = request.json or {}
    page_num = data.get("page_num")
    center_x = data.get("center_x")
    center_y = data.get("center_y")

    if page_num is None or center_x is None or center_y is None:
        return jsonify({"error": "Missing required parameters: page_num, center_x, center_y"}), 400

    try:
        doc = fitz.open(pdf_path)

        # Find the annotation by xref across all pages
        target_annot = None
        target_page = None
        for pg in doc:
            for annot in pg.annots() or []:
                if annot.xref == xref:
                    target_annot = annot
                    target_page = pg
                    break
            if target_annot:
                break

        if not target_annot:
            doc.close()
            return jsonify({"error": "Stamp not found"}), 404

        # Read stamp identifiers (same logic as delete_stamp)
        stamp_id   = target_annot.info.get("name", "")
        uuid_val   = doc.xref_get_key(xref, "StampID")
        stamp_uuid = ""
        if uuid_val[0] == "string":
            v = uuid_val[1]
            stamp_uuid = v[1:-1] if (v.startswith("(") and v.endswith(")")) else v

        # Preserve visual (screen-space) size of the stamp.
        # target_annot.rect is in unrotated PDF coords; multiplying by the rotation
        # matrix gives the visual rect so width/height match what the user sees.
        visual_src_rect = target_annot.rect * target_page.rotation_matrix
        orig_w = visual_src_rect.width
        orig_h = visual_src_rect.height

        # Destination page
        dest_page = doc[int(page_num) - 1]

        # Map visual center → unrotated PDF coords
        visual_rect = fitz.Rect(
            float(center_x) - orig_w / 2,
            float(center_y) - orig_h / 2,
            float(center_x) + orig_w / 2,
            float(center_y) + orig_h / 2,
        )
        new_rect = visual_rect * ~dest_page.rotation_matrix

        def find_and_move_link(src_page, dst_page, dst_rect):
            """Find the stamp's hyperlink on src_page and move it to dst_page at dst_rect."""
            matched = None
            for lnk in src_page.get_links():
                uri = lnk.get("uri", "")
                if stamp_id and f"#stamp-{stamp_id}" in uri:
                    matched = lnk; break
                if stamp_uuid and f"#stamp-{stamp_uuid}" in uri:
                    matched = lnk; break
                # Fallback: overlap with old annot rect
                lnk_from = lnk.get("from")
                if lnk_from:
                    lnk_rect = fitz.Rect(lnk_from)
                    old_area = target_annot.rect.get_area()
                    if old_area > 0 and (lnk_rect & target_annot.rect).get_area() / old_area > 0.5:
                        if "tabsoftwear.salcerandco.com" in uri or "#stamp-" in uri:
                            matched = lnk; break
            if matched:
                src_page.delete_link(matched)
                new_lnk = dict(matched)
                new_lnk["from"] = dst_rect
                dst_page.insert_link(new_lnk)

        if target_page.number != dest_page.number:
            # Cross-page: recreate annotation on new page, delete original
            new_annot = dest_page.add_freetext_annot(
                new_rect,
                target_annot.get_text(),
                fontsize=max(min(new_rect.width, new_rect.height) * 0.5, 6.0),
                fontname="helv",
                text_color=target_annot.colors.get("stroke", (1, 0, 0)),
                fill_color=target_annot.colors.get("fill", (1, 1, 1)),
                align=fitz.TEXT_ALIGN_CENTER,
            )
            new_annot.set_border(width=2.0)
            info = target_annot.info
            new_annot.set_info(subject=info.get("subject", ""), title=info.get("title", ""))
            new_annot.update()
            # Copy custom PDF keys (Subtype, NM, Name, StampID, PatternName)
            for key in ("Subtype", "NM", "Name", "StampID", "PatternName"):
                val = doc.xref_get_key(xref, key)
                if val and val[0] != "null":
                    doc.xref_set_key(new_annot.xref, key, val[1])
            # Move hyperlink before deleting original
            find_and_move_link(target_page, dest_page, new_rect)
            target_page.delete_annot(target_annot)
            result_xref = new_annot.xref
        else:
            # Same page: update the Rect using set_rect which safely updates the PDF dictionary
            # and properly handles unrotated top-left to unrotated bottom-left transformations.
            target_annot.set_rect(new_rect)
            # Move hyperlink
            find_and_move_link(dest_page, dest_page, new_rect)
            result_xref = xref

        result_rect = [visual_rect.x0, visual_rect.y0, visual_rect.x1, visual_rect.y1]

        try:
            doc.saveIncr()
            doc.close()
        except Exception:
            tmp_path = pdf_path + ".tmp"
            doc.save(tmp_path, deflate=True)
            doc.close()
            os.replace(tmp_path, pdf_path)
            
        try:
            project = filename.split("/")[1] if filename.startswith("Projects/") else (filename.split("/")[1] if filename.lower().startswith("output/") else "default")
            import stamp_db
            stamp_db.update_stamp_location(project, pdf_path, xref, result_xref, int(page_num))
        except Exception as e:
            print("Failed to update stamp location in DB:", e)

        return jsonify({
            "success": True,
            "xref": result_xref,
            "page_num": int(page_num),
            "rect": result_rect,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/stamps/<int:xref>/explode", methods=["POST"])
@api_login_required
def explode_stamp(filename, xref):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404
        
    try:
        doc = fitz.open(pdf_path)
        target_annot = None
        target_page = None
        for page in doc:
            for annot in page.annots() or []:
                if annot.xref == xref:
                    target_annot = annot
                    target_page = page
                    break
            if target_annot:
                break
                
        if not target_annot:
            doc.close()
            return jsonify({"error": "Stamp not found"}), 404
            
        ap_val = doc.xref_get_key(xref, "AP")[1]
        if not ap_val.startswith("<<"):
            raise ValueError("Stamp has no appearance dictionary")
            
        import re
        m = re.search(r"/N\s+(\d+)\s+0\s+R", ap_val)
        if not m:
            raise ValueError("Stamp appearance dict has no /N stream")
            
        xobj_xref = int(m.group(1))
        bbox_str = doc.xref_get_key(xobj_xref, "BBox")[1].strip("[]")
        bx0, by0, bx1, by1 = map(float, bbox_str.split())
        
        rect_str = doc.xref_get_key(xref, "Rect")[1].strip("[]")
        rx0, ry0, rx1, ry1 = map(float, rect_str.split())
        
        bw, bh = bx1 - bx0, by1 - by0
        rw, rh = rx1 - rx0, ry1 - ry0
        
        sx = rw / bw if bw else 1.0
        sy = rh / bh if bh else 1.0
        ex = rx0 - bx0 * sx
        ey = ry0 - by0 * sy
        
        name = f"FmStamp{xref}"
        target_page.clean_contents()
        doc.xref_set_key(target_page.xref, f"Resources/XObject/{name}", f"{xobj_xref} 0 R")
        
        contents_xref = target_page.get_contents()[0]
        cmd = f"\nq\n{sx:g} 0 0 {sy:g} {ex:g} {ey:g} cm\n/{name} Do\nQ\n"
        
        stream = doc.xref_stream(contents_xref)
        doc.update_stream(contents_xref, stream + cmd.encode('latin1'))
        
        # Clean up associated hyperlink before deleting the stamp annotation
        stamp_id = target_annot.info.get("name")
        stamp_uuid_val = target_page.parent.xref_get_key(target_annot.xref, "StampID")
        stamp_uuid = ""
        if stamp_uuid_val[0] == "string":
            val = stamp_uuid_val[1]
            if val.startswith("(") and val.endswith(")"):
                stamp_uuid = val[1:-1]
            else:
                stamp_uuid = val
                
        links_to_delete = []
        for link in target_page.get_links():
            uri = link.get("uri", "")
            if stamp_id and f"#stamp-{stamp_id}" in uri:
                links_to_delete.append(link)
            elif stamp_uuid and f"#stamp-{stamp_uuid}" in uri:
                links_to_delete.append(link)
            elif link.get("from") and (link["from"] & target_annot.rect).get_area() / target_annot.rect.get_area() > 0.8:
                if "tabsoftwear.salcerandco.com" in uri or "#stamp-" in uri:
                    links_to_delete.append(link)
        for link in links_to_delete:
            try:
                target_page.delete_link(link)
            except Exception:
                pass

        target_page.delete_annot(target_annot)
        
        # Try to save incrementally first to avoid WinError 5 (file lock) on Windows
        try:
            doc.saveIncr()
            doc.close()
        except Exception:
            # Fallback to saving to a temp file and replacing if incremental save is not possible
            tmp_path = pdf_path + ".tmp"
            doc.save(tmp_path, deflate=True)
            doc.close()
            os.replace(tmp_path, pdf_path)
        
        # Clean up database record
        try:
            stamp_db.delete_stamp_record(get_project_name_from_pdf_path(pdf_path), pdf_path, xref)
        except Exception:
            pass

        return jsonify({"success": True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/pdf/<path:filename>/stamps/copy", methods=["POST"])
@api_login_required
def copy_stamp(filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    data = request.json or {}
    src_xref = data.get("source_xref")
    src_page = data.get("source_page")
    new_name = data.get("new_name")
    new_uuid = data.get("new_uuid")
    page_num = data.get("page_num")
    center_x = data.get("center_x")
    center_y = data.get("center_y")

    required_params = {"source_xref": src_xref, "source_page": src_page, "new_name": new_name, 
                       "new_uuid": new_uuid, "page_num": page_num, "center_x": center_x, "center_y": center_y}
    missing = [k for k, v in required_params.items() if v is None]
    if missing:
        return jsonify({"error": f"Missing required parameters: {', '.join(missing)}"}), 400

    try:
        doc = fitz.open(pdf_path)
        src_page_obj = doc[int(src_page) - 1]
        page = doc[int(page_num) - 1]
        
        src_annot = None
        for a in src_page_obj.annots() or []:
            if a.xref == int(src_xref):
                src_annot = a
                break
                
        if not src_annot:
            doc.close()
            return jsonify({"error": "Source stamp not found"}), 404

        # Get visual width and height of the source stamp
        visual_src_rect = src_annot.rect * src_page_obj.rotation_matrix
        visual_w = visual_src_rect.width
        visual_h = visual_src_rect.height
        
        # Create target visual rect centered at center_x, center_y
        target_visual_rect = fitz.Rect(float(center_x) - visual_w/2, float(center_y) - visual_h/2, 
                                       float(center_x) + visual_w/2, float(center_y) + visual_h/2)
        
        # Map back to target page's unrotated coordinates
        new_rect = target_visual_rect * ~page.rotation_matrix
        
        parts = new_name.rsplit('_', 1)
        num_text = parts[1] if len(parts) > 1 else "1"
        
        fixed_fs = max(min(new_rect.width, new_rect.height) * 0.5, 6.0)
        label_color = [1.0, 0.0, 0.0] # Red text like detect_patterns_output.py
        
        new_annot = page.add_freetext_annot(
            new_rect,
            num_text,
            fontsize=fixed_fs,
            fontname="helv",
            text_color=label_color,
            fill_color=(1.0, 1.0, 1.0),
            align=fitz.TEXT_ALIGN_CENTER,
        )
        new_annot.set_border(width=2.0)
        stamp_subject = src_annot.info.get("subject", "system")
        new_annot.set_info(subject=stamp_subject, title="")
        new_annot.set_rotation(page.rotation)
        new_annot.update()

        import urllib.parse
        encoded_pdf = urllib.parse.quote(pdf_path.replace("\\", "/"))
        base_url = "https://tabsoftwear.salcerandco.com/"
        link = {
            "kind": fitz.LINK_URI,
            "from": new_rect,
            "uri": f"{base_url}?pdf={encoded_pdf}#stamp-{new_uuid}"
        }
        page.insert_link(link)
        
        doc.xref_set_key(new_annot.xref, "Subtype", "/Stamp")
        doc.xref_set_key(new_annot.xref, "NM", f"({new_name})")
        doc.xref_set_key(new_annot.xref, "Name", f"/{new_uuid}")
        doc.xref_set_key(new_annot.xref, "StampID", f"({new_uuid})")
        
        # Determine OCG if possible from source annot link
        for lnk in src_page_obj.get_links():
            if lnk.get("from") and (lnk["from"] & src_annot.rect).get_area() / src_annot.rect.get_area() > 0.8:
                # Find the xref of this link to get its OCG
                annots_val = doc.xref_get_key(src_page_obj.xref, "Annots")
                if annots_val[0] == "array":
                    # PDF array tokens look like "12 0 R 15 0 R" — only numeric
                    # tokens are xrefs; skip "0" generation numbers and "R" keywords.
                    parts_arr = annots_val[1].replace("[", "").replace("]", "").split()
                    for axref in parts_arr:
                        if not axref.isdigit(): continue  # skip "R" and other non-integers
                        axref_int = int(axref)
                        if axref_int == 0: continue
                        ocg_val = doc.xref_get_key(axref_int, "OC")
                        if ocg_val[0] == "indirect":
                            doc.xref_set_key(new_annot.xref, "OC", f"{ocg_val[1]} 0 R")
                            break
                break

        try:
            doc.saveIncr()
            doc.close()
        except Exception:
            tmp_path = pdf_path + ".tmp"
            doc.save(tmp_path, deflate=True)
            doc.close()
            os.replace(tmp_path, pdf_path)
            
        return jsonify({
            "success": True, 
            "stamp": {
                "xref": new_annot.xref,
                "name": new_name,
                "uuid": new_uuid
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- Pattern APIs ---

def get_project_patterns_dir(project_name):
    import re
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_dir = os.path.join(PROJECTS_DIR, sanitized_proj)
    patterns_dir = os.path.join(proj_dir, "patterns")
    os.makedirs(patterns_dir, exist_ok=True)
    return patterns_dir


def normalize_pattern_type(value):
    normalized = (value or "").strip().lower()
    if normalized in {"grill", "air outlet", "air_outlet", "vent"}:
        return "grill"
    if normalized in {"aac", "aac_unit", "hvac", "hvac_unit", "system", "box"}:
        return "aac_unit"
    return normalized or "pattern"

@app.route("/api/projects/<project_name>/pdf/<path:filename>/patterns", methods=["GET"])
@api_login_required
def get_pdf_patterns(project_name, filename):
    pdf_name = os.path.basename(filename)
    patterns_dir = get_project_patterns_dir(project_name)
    pattern_file = os.path.join(patterns_dir, f"{pdf_name}_patterns.json")
    
    if not os.path.exists(pattern_file):
        return jsonify([])
    try:
        with open(pattern_file, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/pdf/<path:filename>/patterns", methods=["POST"])
@api_login_required
def add_pdf_pattern(project_name, filename):
    pdf_name = os.path.basename(filename)
    patterns_dir = get_project_patterns_dir(project_name)
    pattern_file = os.path.join(patterns_dir, f"{pdf_name}_patterns.json")
    
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    item_type = normalize_pattern_type(data.get("type", ""))
    page_num = data.get("page_num")
    vectors = data.get("vectors", [])
    
    if not name or not item_type or page_num is None:
        return jsonify({"error": "Missing required fields"}), 400
        
    patterns = []
    if os.path.exists(pattern_file):
        try:
            with open(pattern_file, "r", encoding="utf-8") as f:
                patterns = json.load(f)
        except Exception:
            patterns = []
            
    import time
    new_id = f"pattern_{int(time.time() * 1000)}"
    new_pattern = {
        "id": new_id,
        "name": name,
        "type": item_type,
        "page_num": int(page_num),
        "vectors": vectors,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    
    patterns.append(new_pattern)
    
    try:
        with open(pattern_file, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=4)
        return jsonify({"success": True, "pattern": new_pattern})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/pdf/<path:filename>/patterns/<pattern_id>", methods=["PATCH"])
@api_login_required
def update_pdf_pattern(project_name, filename, pattern_id):
    pdf_name = os.path.basename(filename)
    patterns_dir = get_project_patterns_dir(project_name)
    pattern_file = os.path.join(patterns_dir, f"{pdf_name}_patterns.json")

    if not os.path.exists(pattern_file):
        return jsonify({"error": "Pattern not found"}), 404

    data = request.get_json() or {}
    vectors = data.get("vectors", [])
    page_num = data.get("page_num")

    try:
        with open(pattern_file, "r", encoding="utf-8") as f:
            patterns = json.load(f)

        updated = None
        for p in patterns:
            if p.get("id") == pattern_id:
                p["vectors"] = vectors
                if page_num is not None:
                    p["page_num"] = int(page_num)
                import time
                p["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                updated = p
                break

        if updated is None:
            return jsonify({"error": "Pattern not found"}), 404

        with open(pattern_file, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=4)

        return jsonify({"success": True, "pattern": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/pdf/<path:filename>/patterns/<pattern_id>", methods=["DELETE"])
@api_login_required
def delete_pdf_pattern(project_name, filename, pattern_id):
    pdf_name = os.path.basename(filename)
    patterns_dir = get_project_patterns_dir(project_name)
    pattern_file = os.path.join(patterns_dir, f"{pdf_name}_patterns.json")
    
    if not os.path.exists(pattern_file):
        return jsonify({"error": "Pattern not found"}), 404
        
    try:
        with open(pattern_file, "r", encoding="utf-8") as f:
            patterns = json.load(f)
            
        initial_count = len(patterns)
        patterns = [p for p in patterns if p.get("id") != pattern_id]
        
        if len(patterns) == initial_count:
            return jsonify({"error": "Pattern not found"}), 404
            
        with open(pattern_file, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=4)
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<path:project_name>/data", methods=["GET"])
@api_login_required
def get_project_data(project_name):
    try:
        data = stamp_db.get_all_project_data(project_name)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<path:project_name>/sync-from-pdf", methods=["POST"])
@api_login_required
def sync_from_pdf(project_name):
    """
    Syncs stamp data from all PDFs in the project into the database.

    Matching is done exclusively by UUID (StampID annotation key).

    - UUID in PDF but not DB  → add new DB record
    - UUID in both            → update pdf_path, page, xref, pattern_name, stamp_type, # field
                                delete any duplicate DB rows for that UUID
    - UUID in DB but not PDF  → mark pattern_name='NOT FOUND', #='NOT FOUND'

    Field mapping:
      PDF PatternName (or fallback: annotation 'name') → split into:
        pattern_part + number_part → DB pattern_name = "<pattern>_<number>", # = "<number>"
      PDF subject ('system' / 'air outlet') → DB stamp_type
    """
    import re as _re
    sanitized_proj = _re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_pdfs_dir = os.path.join(PROJECTS_DIR, sanitized_proj, "pdfs")

    if not os.path.exists(proj_pdfs_dir):
        return jsonify({"error": "Project not found"}), 404

    # UUID regex — detect when the annotation name IS just a UUID (no real pattern set)
    # We use a slightly more permissive UUID regex to handle faulty tools that might omit hyphens
    # or format it as e.g. 8-4-4-16 instead of 8-4-4-4-12.
    UUID_RE = _re.compile(
        r'^[0-9a-f\-]{32,36}$',
        _re.IGNORECASE
    )

    def parse_raw_name(raw_name, stamp_uuid):
        """
        Parse a raw annotation name into (pattern_part, number_part, db_pattern_name).
        Returns None tuple when raw_name looks like a bare UUID (no useful pattern info).
        """
        if not raw_name or UUID_RE.match(raw_name.strip()):
            return None, None, None  # No useful pattern — skip overwrite

        # Try to split trailing number: "TypeA 3", "TypeA_3", "small dr ao 1"
        m = _re.search(r'^(.*?)[\s_\-](\d+)\s*$', raw_name)
        if m:
            pattern_part = m.group(1).strip()
            number_part  = m.group(2).strip()
            db_pattern_name = f"{pattern_part}_{number_part}"
        else:
            pattern_part    = raw_name.strip()
            number_part     = raw_name.strip()
            db_pattern_name = raw_name.strip()

        return pattern_part, number_part, db_pattern_name

    try:
        # ── Step 1: Collect all stamp data from all PDFs ──────────────────────
        # pdf_stamps: uuid → {pdf_path, page, xref, pattern_name, pattern_part, number_part, stamp_type}
        pdf_stamps = {}
        pdf_files = sorted([
            os.path.join(proj_pdfs_dir, f)
            for f in os.listdir(proj_pdfs_dir)
            if f.lower().endswith(".pdf")
        ])

        for pdf_path in pdf_files:
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    for annot in page.annots() or []:
                        if annot.type[1] != "Stamp":
                            continue

                        # ── Read UUID ────────────────────────────────────────
                        # StampID key = UUID string  e.g. (fbc3584d-...)
                        # Name key    = /UUID  (PDF name object = annot.info["name"])
                        # NM key      = pattern+number  e.g. (small dr ao_1)  (= annot.info["id"])
                        uuid_val = page.parent.xref_get_key(annot.xref, "StampID")
                        stamp_uuid = ""
                        if uuid_val[0] == "string":
                            v = uuid_val[1]
                            stamp_uuid = v[1:-1] if (v.startswith("(") and v.endswith(")")) else v
                        if not stamp_uuid:
                            # fallback: Name key is /UUID (name object, no parens)
                            name_val = page.parent.xref_get_key(annot.xref, "Name")
                            if name_val[0] == "name":
                                stamp_uuid = name_val[1].lstrip("/")
                        if not stamp_uuid:
                            # last resort: annot.info["name"] also reads the Name key
                            n = annot.info.get("name") or ""
                            if UUID_RE.match(n.strip()):
                                stamp_uuid = n.strip()
                        if not stamp_uuid:
                            continue  # no UUID → skip

                        # ── Read Pattern+Number (from NM / PatternName) ───────
                        # Priority:
                        #   1. PatternName custom key (set by web scanner)
                        #   2. NM key directly = annot.info["id"]  (set by detect_patterns_output.py)
                        #   3. NM key via xref_get_key as fallback
                        def _read_str_key(xref_id, key):
                            val_tuple = page.parent.xref_get_key(xref_id, key)
                            if val_tuple[0] == "string":
                                v = val_tuple[1]
                                return v[1:-1] if (v.startswith("(") and v.endswith(")")) else v
                            return ""

                        pattern_name_key = _read_str_key(annot.xref, "PatternName")
                        nm_key           = _read_str_key(annot.xref, "NM")
                        annot_id         = annot.info.get("id") or ""  # reads NM key

                        # Prefer PatternName (web scanner); then NM key; then annot.id
                        raw_name = pattern_name_key or nm_key or annot_id

                        pattern_part, number_part, db_pattern_name = parse_raw_name(raw_name, stamp_uuid)

                        # ── Read stamp type from subject ──────────────────────
                        subject    = (annot.info.get("subject") or "").lower().strip()
                        stamp_type = "system" if "system" in subject else "air_outlet"

                        # Only overwrite an earlier entry for this UUID if the new
                        # entry has a real pattern (not None)
                        if stamp_uuid not in pdf_stamps or db_pattern_name is not None:
                            pdf_stamps[stamp_uuid] = {
                                "pdf_path":     pdf_path,
                                "page":         page_num + 1,
                                "xref":         annot.xref,
                                "pattern_name": db_pattern_name,   # may be None
                                "pattern_part": pattern_part,
                                "number_part":  number_part,
                                "stamp_type":   stamp_type,
                            }

                doc.close()
            except Exception as pdf_err:
                print(f"sync-from-pdf: Error reading {pdf_path}: {pdf_err}")
                continue

        # ── Step 2: Load ALL DB stamp rows, grouped by UUID ───────────────────
        # Each UUID may have multiple rows (from different pdf_path registrations).
        db_data = stamp_db.get_all_project_data_raw(sanitized_proj)

        # db_by_uuid: uuid → list of DB rows (sorted by id ascending = oldest first)
        from collections import defaultdict
        db_groups = defaultdict(list)
        for row in db_data:
            uuid = row.get("stamp_uuid") or ""
            if uuid:
                db_groups[uuid].append(row)
            # rows without uuid can't be matched — leave them alone

        added            = 0
        updated          = 0
        not_found_marked = 0
        duplicates_removed = 0

        # ── Step 3: PDF stamps → update or create DB rows ─────────────────────
        for uuid, pdf_info in pdf_stamps.items():
            db_rows = db_groups.get(uuid, [])

            if db_rows:
                # Sort so the row with the SAME pdf_path comes first;
                # otherwise take the oldest row (lowest id).
                norm_pdf = stamp_db.normalize_db_path(pdf_info["pdf_path"])
                db_rows_sorted = sorted(
                    db_rows,
                    key=lambda r: (
                        0 if stamp_db.normalize_db_path(r["pdf_path"]) == norm_pdf else 1,
                        r["id"]
                    )
                )
                primary = db_rows_sorted[0]
                duplicates = db_rows_sorted[1:]

                stamp_id = primary["id"]

                # Update location + pattern + type on the primary row
                changed = stamp_db.sync_update_stamp(
                    sanitized_proj,
                    stamp_id,
                    new_pdf_path    = pdf_info["pdf_path"],
                    new_page        = pdf_info["page"],
                    new_xref        = pdf_info["xref"],
                    new_pattern_name= pdf_info["pattern_name"],   # may be None → don't overwrite
                    new_stamp_type  = pdf_info["stamp_type"],
                    new_number      = pdf_info["number_part"],
                )
                if changed:
                    updated += 1

                # Delete duplicate rows (same UUID, different pdf_path entry)
                for dup in duplicates:
                    stamp_db.delete_stamp_by_id(sanitized_proj, dup["id"])
                    duplicates_removed += 1

            else:
                # UUID not in DB at all → insert
                if pdf_info["pattern_name"] is not None:
                    db_pattern = pdf_info["pattern_name"]
                    db_number  = pdf_info["number_part"]
                else:
                    db_pattern = ""
                    db_number  = ""

                stamp_id = stamp_db.get_or_create_stamp(
                    sanitized_proj,
                    pdf_info["pdf_path"],
                    pdf_info["page"],
                    pdf_info["xref"],
                    stamp_type   = pdf_info["stamp_type"],
                    pattern_name = db_pattern,
                    stamp_uuid   = uuid,
                )
                stamp_db.update_stamp_field_bulk(sanitized_proj, [
                    (stamp_id, "#", db_number, db_pattern)
                ])
                added += 1

        # ── Step 4: DB UUIDs not found in any PDF → mark NOT FOUND ───────────
        for uuid, db_rows in db_groups.items():
            if uuid not in pdf_stamps:
                for db_row in db_rows:
                    stamp_db.update_stamp_field_bulk(sanitized_proj, [
                        (db_row["id"], "#", "NOT FOUND", "NOT FOUND")
                    ])
                    stamp_db.mark_stamp_not_found(sanitized_proj, db_row["id"])
                    not_found_marked += 1

        return jsonify({
            "success":           True,
            "added":             added,
            "updated":           updated,
            "not_found_marked":  not_found_marked,
            "duplicates_removed":duplicates_removed,
            "total_pdf_stamps":  len(pdf_stamps),
            "total_db_stamps":   len(db_data),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@app.route("/api/stamps/<path:project_name>/<path:pdf_name>/<int:page>/<int:xref>", methods=["GET"])
@api_login_required
def get_stamp_meta(project_name, pdf_name, page, xref):
    resolved_path = get_pdf_path(pdf_name) or pdf_name
    stamp_type = None
    try:
        import fitz
        doc = fitz.open(resolved_path)
        pg = doc[page - 1]
        for annot in pg.annots() or []:
            if annot.xref == xref:
                subject = (annot.info.get("subject") or "").lower().strip()
                if "system" in subject:
                    stamp_type = "system"
                elif "air outlet" in subject or "grill" in subject:
                    stamp_type = "air_outlet"
                break
        doc.close()
    except Exception:
        pass

    stamp_id = stamp_db.get_or_create_stamp(project_name, resolved_path, page, xref, stamp_type=stamp_type)
    meta = stamp_db.get_stamp_metadata(project_name, stamp_id)
    return jsonify({"success": True, "stamp_id": stamp_id, "metadata": meta})

@app.route("/api/stamps/<path:project_name>/<path:pdf_name>/<int:page>/<int:xref>", methods=["POST"])
@api_login_required
def update_stamp_meta(project_name, pdf_name, page, xref):
    data = request.json or {}
    resolved_path = get_pdf_path(pdf_name) or pdf_name
    stamp_id = stamp_db.get_or_create_stamp(project_name, resolved_path, page, xref)
    
    fields = data.get("fields")
    if fields is not None:
        stamp_db.upsert_fields(project_name, stamp_id, fields)
        
    group_id = data.get("group_id")
    if "group_id" in data:
        stamp_db.assign_group(project_name, stamp_id, group_id)
        
    pattern_name = data.get("pattern_name")
    if pattern_name:
        with stamp_db._lock:
            conn = stamp_db._get_connection(project_name)
            try:
                conn.execute("UPDATE stamps SET pattern_name=? WHERE id=?", (pattern_name, stamp_id))
                conn.commit()
            finally:
                conn.close()

    stamp_type = data.get("stamp_type")
    if stamp_type or pattern_name:
        if stamp_type:
            stamp_db.update_stamp_type(project_name, stamp_id, stamp_type)
        try:
            import fitz
            doc = fitz.open(resolved_path)
            p = doc.load_page(page - 1)
            for annot in p.annots():
                if annot.xref == int(xref):
                    info = annot.info
                    if stamp_type:
                        info["subject"] = "System" if stamp_type == "system" else "Air Outlet"
                    annot.set_info(info)
                    annot.update()
                    if pattern_name:
                        doc.xref_set_key(annot.xref, "PatternName", f"({pattern_name})")
                    break
            doc.saveIncr()
            doc.close()
        except Exception as e:
            print("Failed to update PDF stamp_type or pattern_name:", e)
            
    return jsonify({"success": True})

@app.route("/api/config/data_viewer", methods=["GET"])
@api_login_required
def get_data_viewer_config():
    config = load_config()
    dv_config = config.get("data_viewer", {})
    return jsonify(dv_config)

@app.route("/api/config/data_viewer", methods=["POST"])
@api_login_required
def update_data_viewer_config():
    data = request.json or {}
    config = load_config()
    config["data_viewer"] = data
    save_config(config)
    return jsonify({"success": True})

@app.route("/api/update_server", methods=["POST"])
@api_login_required
def update_server():
    try:
        import subprocess
        import threading
        import time

        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Git Pull
        pull_res = subprocess.run(
            ["git", "pull"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=True
        )

        # Read systemd unit file if exists for debugging
        service_content = ""
        service_path = "/etc/systemd/system/pinchus.service"
        if os.path.exists(service_path):
            try:
                with open(service_path, "r") as f:
                    service_content = f"\n\n--- pinchus.service ---\n{f.read()}"
            except Exception as e:
                service_content = f"\n\n--- pinchus.service error ---\nCould not read service file: {e}"

        def restart_gunicorn():
            time.sleep(1)
            if os.name != 'nt':
                subprocess.run(["systemctl", "restart", "pinchus"])

        threading.Thread(target=restart_gunicorn).start()

        return jsonify({
            "success": True,
            "output": pull_res.stdout + service_content
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/invite_code", methods=["GET", "POST"])
@api_login_required
def manage_invite_code():
    if session.get("username") != "admin":
        return jsonify({"error": "Unauthorized"}), 403
        
    config = load_config()
    import time
    
    if request.method == "POST":
        import random
        import string
        chars = "".join(c for c in string.ascii_uppercase + string.digits if c not in "O0I1")
        new_code = "".join(random.choice(chars) for _ in range(8))
        config["invite_code"] = new_code
        config["invite_code_created_at"] = time.time()
        save_config(config)
        
        base_url = request.host_url.rstrip('/')
        invite_url = f"{base_url}/register?code={new_code}"
        return jsonify({
            "success": True, 
            "invite_code": new_code, 
            "invite_url": invite_url,
            "expires_in_hours": 24
        })
        
    invite_code = config.get("invite_code", "")
    created_at = config.get("invite_code_created_at", 0)
    base_url = request.host_url.rstrip('/')
    
    is_expired = False
    if invite_code and (time.time() - created_at > 86400):
        is_expired = True
        config["invite_code"] = ""
        save_config(config)
        
    invite_url = f"{base_url}/register?code={invite_code}" if invite_code and not is_expired else ""
    expires_in_hours = max(0, int((created_at + 86400 - time.time()) / 3600)) if invite_code and not is_expired else 0
    
    return jsonify({
        "invite_code": invite_code if not is_expired else "",
        "invite_url": invite_url,
        "expires_in_hours": expires_in_hours
    })

@app.route("/api/groups/<path:project_name>", methods=["GET"])
@api_login_required
def get_groups(project_name):
    groups = stamp_db.list_groups(project_name)
    return jsonify({"success": True, "groups": groups})

@app.route("/api/groups/<path:project_name>", methods=["POST"])
@api_login_required
def create_new_group(project_name):
    data = request.json or {}
    name = data.get("name")
    color = data.get("color", "#000000")
    if not name:
        return jsonify({"error": "Group name is required"}), 400
    group_id = stamp_db.create_group(project_name, name, color)
    return jsonify({"success": True, "group_id": group_id})

# --- Report Template API Endpoints ---

def get_project_templates_dir(project_name):
    sanitized_proj = re.sub(r'[^a-zA-Z0-9_\-\s]', '', project_name).strip()
    proj_dir = os.path.join(PROJECTS_DIR, sanitized_proj)
    tpl_dir = os.path.join(proj_dir, "templates")
    os.makedirs(tpl_dir, exist_ok=True)
    return tpl_dir

@app.route("/api/projects/<project_name>/templates", methods=["GET"])
@api_login_required
def list_project_templates(project_name):
    tpl_dir = get_project_templates_dir(project_name)
    templates = []
    try:
        for entry in os.scandir(tpl_dir):
            if entry.is_file() and entry.name.lower().endswith(".docx"):
                templates.append({
                    "name": entry.name,
                    "path": entry.name
                })
        templates.sort(key=lambda t: t["name"].lower())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(templates)

@app.route("/api/projects/<project_name>/templates/upload", methods=["POST"])
@api_login_required
def upload_project_template(project_name):
    tpl_dir = get_project_templates_dir(project_name)
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400
    if file and file.filename.lower().endswith('.docx'):
        filename = file.filename
        name, ext = os.path.splitext(os.path.basename(filename))
        name = re.sub(r'[^a-zA-Z0-9_\-\s]', '', name).strip()
        safe_filename = name + ext.lower()
        target_path = os.path.join(tpl_dir, safe_filename)
        try:
            file.save(target_path)
            return jsonify({"success": True, "name": safe_filename}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "Only DOCX files are allowed"}), 400

@app.route("/api/projects/<project_name>/pdf/<path:filename>/render", methods=["POST"])
@api_login_required
def render_pdf_report(project_name, filename):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404
        
    data = request.json or {}
    template_name = data.get("template_name")
    if not template_name:
        return jsonify({"error": "Template name is required"}), 400
        
    tpl_dir = get_project_templates_dir(project_name)
    template_path = os.path.join(tpl_dir, template_name)
    if not os.path.exists(template_path):
        return jsonify({"error": "Template not found"}), 404
        
    # Gather stamps data for the current PDF
    stamps_data = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            for annot in page.annots() or []:
                if annot.type[1] == "Stamp":
                    subject = (annot.info.get("subject") or "").lower().strip()
                    type_val = "system" if "system" in subject else "air_outlet"
                    stamp_id = stamp_db.get_or_create_stamp(project_name, pdf_path, page_num + 1, annot.xref, stamp_type=type_val)
                    meta = stamp_db.get_stamp_metadata(project_name, stamp_id)
                    stamps_data.append({
                        "xref": annot.xref,
                        "page_num": page_num + 1,
                        "fields": meta.get("fields", [])
                    })
        doc.close()
    except Exception as e:
        return jsonify({"error": f"Failed to load stamp data: {str(e)}"}), 500
        
    # Sort stamps by page and position, or by the # (pattern number) if available
    def get_stamp_sort_key(s):
        for f in s.get("fields", []):
            if f["name"] == "#" and f["value"]:
                try:
                    return (0, int(f["value"]))
                except ValueError:
                    return (1, f["value"])
        return (2, s["page_num"], s["xref"])
        
    stamps_data.sort(key=get_stamp_sort_key)
    
    # Generate report
    output_filename = f"Report_{os.path.splitext(os.path.basename(pdf_path))[0]}.docx"
    output_path = os.path.join(BASE_DIR, "web_viewer", "data", "projects", output_filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        # Load user mapping if it exists
        mapping_file = os.path.join(tpl_dir, f"{template_name}_mapping.json")
        user_mapping = {}
        if os.path.exists(mapping_file):
            with open(mapping_file, "r", encoding="utf-8") as f:
                user_mapping = json.load(f)

        doc_renderer.populate_docx_template(template_path, output_path, stamps_data, user_mapping)
        return send_file(
            output_path,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            as_attachment=True,
            download_name=output_filename
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Rendering failed: {str(e)}"}), 500

@app.route("/api/projects/<project_name>/fields", methods=["GET"])
@api_login_required
def get_project_fields(project_name):
    fields = stamp_db.get_all_project_fields(project_name)
    return jsonify({"success": True, "fields": fields})

@app.route("/api/projects/<project_name>/fields_data", methods=["GET"])
@api_login_required
def get_project_fields_data(project_name):
    fields = stamp_db.get_all_project_fields(project_name)
    fields_data = {}
    for f in fields:
        fields_data[f] = stamp_db.get_field_unique_values(project_name, f)
        
    patterns = stamp_db.get_all_patterns(project_name)
    system_patterns = stamp_db.get_all_system_patterns(project_name)
    
    return jsonify({
        "success": True,
        "fields": fields,
        "fields_data": fields_data,
        "patterns": patterns,
        "system_patterns": system_patterns
    })

@app.route("/api/projects/<project_name>/templates/<template_name>/columns", methods=["GET"])
@api_login_required
def get_template_columns(project_name, template_name):
    tpl_dir = get_project_templates_dir(project_name)
    template_path = os.path.join(tpl_dir, template_name)
    if not os.path.exists(template_path):
        return jsonify({"error": "Template not found"}), 404
        
    try:
        columns = doc_renderer.extract_template_columns(template_path)
        return jsonify({"success": True, "columns": columns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/templates/<template_name>/preview", methods=["GET"])
@api_login_required
def get_template_preview(project_name, template_name):
    tpl_dir = get_project_templates_dir(project_name)
    template_path = os.path.join(tpl_dir, template_name)
    if not os.path.exists(template_path):
        return jsonify({"error": "Template not found"}), 404
        
    try:
        preview = doc_renderer.extract_table_preview(template_path)
        return jsonify({"success": True, "preview": preview})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/templates/<template_name>/mapping", methods=["GET", "POST"])
@api_login_required
def template_mapping(project_name, template_name):
    tpl_dir = get_project_templates_dir(project_name)
    mapping_file = os.path.join(tpl_dir, f"{template_name}_mapping.json")
    
    if request.method == "GET":
        if not os.path.exists(mapping_file):
            return jsonify({"success": True, "mapping": {}})
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                mapping = json.load(f)
            return jsonify({"success": True, "mapping": mapping})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    if request.method == "POST":
        data = request.json or {}
        mapping = data.get("mapping", {})
        try:
            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump(mapping, f, indent=2)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/projects/<project_name>/templates/<template_name>/download", methods=["GET"])
@api_login_required
def download_template_raw(project_name, template_name):
    tpl_dir = get_project_templates_dir(project_name)
    template_path = os.path.join(tpl_dir, template_name)
    if not os.path.exists(template_path):
        return jsonify({"error": "Template not found"}), 404
        
    return send_file(
        template_path,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name=template_name
    )

@app.route("/api/projects/<project_name>/templates/<template_name>/preview_html", methods=["GET"])
@api_login_required
def get_template_preview_html(project_name, template_name):
    tpl_dir = get_project_templates_dir(project_name)
    template_path = os.path.join(tpl_dir, template_name)
    if not os.path.exists(template_path):
        return jsonify({"error": "Template not found"}), 404

    # Save HTML in a subfolder named `<template_name>_html`
    html_dir = os.path.join(tpl_dir, f"{template_name}_html")
    os.makedirs(html_dir, exist_ok=True)
    html_path = os.path.join(html_dir, "preview.html")

    if not os.path.exists(html_path):
        if HAS_WIN32COM:
            try:
                pythoncom.CoInitialize()
                word = win32com.client.DispatchEx("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(os.path.abspath(template_path))
                
                # Configure WebOptions for modern browser compatibility and UTF-8
                doc.WebOptions.Encoding = 65001 # msoEncodingUTF8
                doc.WebOptions.RelyOnVML = False
                doc.WebOptions.AllowPNG = True
                doc.WebOptions.OptimizeForBrowser = True
                
                doc.SaveAs2(os.path.abspath(html_path), FileFormat=8) # wdFormatHTML
                doc.Close()
                word.Quit()
            except Exception as e:
                traceback.print_exc()
                return jsonify({"error": f"Failed to convert document: {str(e)}"}), 500
            finally:
                pythoncom.CoUninitialize()
        else:
            try:
                import subprocess
                # Run LibreOffice headless conversion
                cmd = [
                    "libreoffice",
                    "--headless",
                    "--convert-to", "html",
                    "--outdir", html_dir,
                    os.path.abspath(template_path)
                ]
                subprocess.run(cmd, check=True)
                # LibreOffice will create a file named `<template_name_without_ext>.html` in html_dir
                generated_name = f"{os.path.splitext(template_name)[0]}.html"
                generated_path = os.path.join(html_dir, generated_name)
                if os.path.exists(generated_path):
                    # Rename generated file to preview.html
                    if os.path.exists(html_path):
                        os.remove(html_path)
                    os.rename(generated_path, html_path)
                else:
                    # sometimes LibreOffice uses the exact filename with .html appended
                    generated_path_alt = os.path.join(html_dir, f"{template_name}.html")
                    if os.path.exists(generated_path_alt):
                        if os.path.exists(html_path):
                            os.remove(html_path)
                        os.rename(generated_path_alt, html_path)
                    else:
                        raise FileNotFoundError(f"Could not find converted HTML file. Expected at {generated_path}")
            except Exception as e:
                traceback.print_exc()
                return jsonify({"error": f"Failed to convert document via LibreOffice: {str(e)}"}), 500

    return jsonify({"success": True, "url": f"/api/projects/{project_name}/templates/{template_name}/html_asset/preview.html"})

@app.route("/api/projects/<project_name>/templates/<template_name>/html_asset/<path:filename>", methods=["GET"])
def serve_template_html_asset(project_name, template_name, filename):
    tpl_dir = get_project_templates_dir(project_name)
    html_dir = os.path.join(tpl_dir, f"{template_name}_html")
    return send_from_directory(html_dir, filename)

@app.route("/api/global_stamps/<path:filename>")
def serve_global_stamp(filename):
    upload_dir = os.path.join(BASE_DIR, "web_viewer", "data", "global_stamps")
    return send_from_directory(upload_dir, filename)

@app.route("/api/manage_tags/upload", methods=["POST"])
def manage_tags_upload():
    if 'files[]' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    files = request.files.getlist('files[]')
    if not files or (len(files) == 1 and files[0].filename == ''):
        return jsonify({"error": "No files selected"}), 400
        
    upload_dir = os.path.join(BASE_DIR, "web_viewer", "data", "global_stamps")
    os.makedirs(upload_dir, exist_ok=True)
    
    try:
        stamp_names = []
        import uuid
        
        for file in files:
            if file.filename == '':
                continue
                
            if file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                name = os.path.splitext(file.filename)[0]
                safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                ext = os.path.splitext(file.filename)[1]
                img_filename = f"{safe_name}{ext}"
                file.save(os.path.join(upload_dir, img_filename))
                stamp_names.append(safe_name)
            else:
                # Save each PDF to a unique temporary path inside the upload directory
                temp_filename = f"temp_upload_{uuid.uuid4().hex}.pdf"
                temp_path = os.path.join(upload_dir, temp_filename)
                try:
                    file.save(temp_path)
                    doc = fitz.open(temp_path)
                    for page in doc:
                        for annot in page.annots() or []:
                            if annot.type[1] == "Stamp":
                                # Try to get a meaningful name
                                name = annot.info.get("title") or annot.info.get("subject") or annot.info.get("name")
                                if name:
                                    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                                    if safe_name:
                                        stamp_names.append(safe_name)
                                        try:
                                            pix = page.get_pixmap(clip=annot.rect, matrix=fitz.Matrix(2, 2))
                                            img_filename = f"{safe_name}.png"
                                            pix.save(os.path.join(upload_dir, img_filename))
                                            # Also save the PDF so we can copy its vectors later!
                                            import shutil
                                            shutil.copy2(temp_path, os.path.join(upload_dir, f"{safe_name}.pdf"))
                                        except Exception as e:
                                            print(f"Error rendering stamp image {safe_name}: {e}")
                    doc.close()
                finally:
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                        except Exception as e:
                            print(f"Failed to remove temp file {temp_path}: {e}")
        
        # Save to global config
        config_path = os.path.join(BASE_DIR, "global_stamp_config.json")
        config = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
        # Merge new stamps with existing stamps, deduplicate and sort
        existing_stamps = config.get("uploadedStamps", [])
        config["uploadedStamps"] = sorted(list(set(existing_stamps + stamp_names)))
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
        return jsonify({"success": True, "stamps": config["uploadedStamps"]})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/manage_tags/delete_stamp", methods=["POST"])
def delete_global_stamp():
    data = request.json
    stamp_name = data.get("stamp_name")
    if not stamp_name:
         return jsonify({"error": "No stamp name provided"}), 400
         
    try:
        upload_dir = os.path.join(BASE_DIR, "web_viewer", "data", "global_stamps")
        img_path = os.path.join(upload_dir, f"{stamp_name}.png")
        if os.path.exists(img_path):
            os.remove(img_path)
            
        config_path = os.path.join(BASE_DIR, "global_stamp_config.json")
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            if "uploadedStamps" in config and stamp_name in config["uploadedStamps"]:
                config["uploadedStamps"].remove(stamp_name)
                
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)
                
        return jsonify({"success": True})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/api/manage_tags/config", methods=["GET", "POST"])
def manage_tags_config():
    config_path = os.path.join(BASE_DIR, "global_stamp_config.json")
    
    if request.method == "GET":
        if not os.path.exists(config_path):
            return jsonify({"success": True, "config": {"uploadedStamps": [], "rules": []}})
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return jsonify({"success": True, "config": config})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    if request.method == "POST":
        data = request.json or {}
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route("/api/manage_tags/apply_rules", methods=["POST"])
def manage_tags_apply_rules():
    """Evaluate all tag rules and apply shape/color changes to every stamp in the project."""
    data = request.json or {}
    project_name = data.get("project")
    if not project_name:
        return jsonify({"error": "No project specified"}), 400

    # Load global rules config
    config_path = os.path.join(BASE_DIR, "global_stamp_config.json")
    if not os.path.exists(config_path):
        return jsonify({"success": True, "updated": 0, "message": "No rules configured"})

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        return jsonify({"error": f"Failed to read config: {e}"}), 500

    rules = config.get("rules", [])
    if not rules:
        return jsonify({"success": True, "updated": 0, "message": "No rules defined"})

    try:
        stamps = stamp_db.get_all_stamps_for_rules(project_name)
    except Exception as e:
        return jsonify({"error": f"Failed to fetch stamps: {e}"}), 500

    updates = []
    logs = []
    
    def add_log(msg):
        logs.append(msg)
        print(msg, flush=True)

    add_log(f"--- Applying rules for project '{project_name}' ---")
    add_log(f"Loaded {len(rules)} rules and {len(stamps)} stamps")

    for stamp in stamps:
        stamp_type = stamp.get("stamp_type") or "air_outlet"
        pattern_name = stamp.get("pattern_name") or ""
        fields = stamp.get("fields") or {}
        stamp_id = stamp["id"]

        for rule in rules:
            rule_field = rule.get("field", "")
            operator = rule.get("operator", "==")
            rule_value = rule.get("value", "")
            rule_result = rule.get("result", "")
            rule_type = rule.get("type", "")

            # Determine the stamp value for the field being checked
            if rule_field == "Target":
                stamp_val = fields.get("Target", "")
            elif rule_field == "Type":
                # Normalize type label to match UI labels
                stamp_val = "System" if stamp_type == "system" else "Air Outlet"
            elif rule_field == "Pattern":
                # Air outlet pattern
                if stamp_type != "system":
                    stamp_val = pattern_name
                else:
                    stamp_val = ""
            elif rule_field == "System":
                # System pattern
                if stamp_type == "system":
                    stamp_val = pattern_name
                else:
                    stamp_val = ""
            else:
                # Arbitrary stamp field
                stamp_val = fields.get(rule_field, "")

            # Evaluate condition
            if operator == "==":
                matches = (stamp_val == rule_value)
            elif operator == "!=":
                matches = (stamp_val != rule_value)
            else:
                matches = False

            if not matches:
                continue

            add_log(f"Stamp {stamp_id} ({stamp_type}, '{pattern_name}') matched rule: IF {rule_field} {operator} '{rule_value}' THEN set {rule_type} to '{rule_result}'")

            if rule_type == "shape" and rule_result:
                current_num = fields.get("#", "")
                if not current_num:
                    import re
                    m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', pattern_name)
                    if m:
                        current_num = m.group(2)
                
                final_pattern_name = rule_result
                if current_num:
                    final_pattern_name = f"{rule_result}_{current_num}"

                updates.append({
                    "stamp_id": stamp_id, 
                    "pattern_name": final_pattern_name,
                    "pdf_path": stamp.get("pdf_path"),
                    "page": stamp.get("page"),
                    "xref": stamp.get("xref")
                })
                add_log(f"  -> Queued shape update for stamp {stamp_id}: {final_pattern_name} (from {rule_result})")
                break  # First matching rule wins for shape
            elif rule_type == "color" and rule_result:
                try:
                    group_id = stamp_db.find_or_create_color_group(project_name, rule_result)
                    updates.append({"stamp_id": stamp_id, "group_id": group_id})
                    add_log(f"  -> Queued color update for stamp {stamp_id}: group_id {group_id} ({rule_result})")
                except Exception as e:
                    add_log(f"  -> Error finding/creating color group: {e}")
                break  # First matching rule wins for color

    try:
        changed = stamp_db.apply_rule_updates(project_name, updates)
        print(f"--- Rule application complete. {changed} stamp updates persisted. ---")
        
        # Now apply the shape updates directly to the underlying PDF files so the UI actually sees the new shapes.
        import fitz
        from collections import defaultdict
        pdf_shape_updates = defaultdict(list)
        for upd in updates:
            if "pattern_name" in upd and upd.get("pdf_path") and upd.get("xref") and upd.get("page"):
                pdf_shape_updates[upd["pdf_path"]].append(upd)
                
        for pdf_path, shape_upds in pdf_shape_updates.items():
            if not os.path.exists(pdf_path):
                print(f"Skipping PDF update: {pdf_path} not found.")
                continue
            try:
                doc = fitz.open(pdf_path)
                pdf_changed = False
                # Group by page to avoid loading pages multiple times unnecessarily
                page_upds = defaultdict(list)
                for u in shape_upds:
                    page_upds[u["page"]].append(u)
                    
                for page_num, upds_for_page in page_upds.items():
                    p = doc.load_page(page_num - 1)
                    for annot in p.annots() or []:
                        for u in upds_for_page:
                            if annot.xref == int(u["xref"]):
                                doc.xref_set_key(annot.xref, "PatternName", f"({u['pattern_name']})")
                                pdf_changed = True
                                
                                # Try to apply the vector drawing from the uploaded shape PDF!
                                # Extract base shape name (e.g. Triangle from Triangle_123)
                                base_shape = u["pattern_name"]
                                import re
                                m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', base_shape)
                                if m:
                                    base_shape = m.group(1)
                                
                                shape_pdf_path = os.path.join(BASE_DIR, "web_viewer", "data", "global_stamps", f"{base_shape}.pdf")
                                if os.path.exists(shape_pdf_path):
                                    try:
                                        src_shape = fitz.open(shape_pdf_path)
                                        doc.insert_pdf(src_shape)
                                        src_shape.close()
                                        
                                        temp_page = doc[-1]
                                        ap_val = None
                                        
                                        # First try: does it have a Stamp annotation?
                                        for copied_annot in temp_page.annots() or []:
                                            if copied_annot.type[1] == "Stamp":
                                                ap_dict = doc.xref_get_key(copied_annot.xref, "AP")
                                                if ap_dict[0] == "dict":
                                                    ap_val = ap_dict[1]
                                                    break
                                                    
                                        # Second try: use the entire page's contents!
                                        if not ap_val:
                                            page_xref = temp_page.xref
                                            res_val = doc.xref_get_key(page_xref, "Resources")
                                            temp_page.clean_contents()
                                            contents_list = temp_page.get_contents()
                                            if contents_list:
                                                contents_xref = contents_list[0]
                                                contents_stream = doc.xref_stream(contents_xref)
                                                new_xobj_xref = doc.get_new_xref()
                                                bbox = temp_page.rect
                                                bbox_str = f"[{bbox.x0} {bbox.y0} {bbox.x1} {bbox.y1}]"
                                                
                                                xobj_dict = f"<< /Type /XObject /Subtype /Form /BBox {bbox_str} /Matrix [1 0 0 1 0 0] "
                                                if res_val[0] == "dict":
                                                    xobj_dict += f"/Resources {res_val[1]} "
                                                xobj_dict += ">>"
                                                
                                                doc.update_object(new_xobj_xref, xobj_dict)
                                                doc.update_stream(new_xobj_xref, contents_stream)
                                                
                                                ap_val = f"<< /N {new_xobj_xref} 0 R >>"
                                                
                                        if ap_val:
                                            # Strip the /AS key from target annot so it doesn't look for a state
                                            doc.xref_set_key(annot.xref, "AS", "null")
                                            doc.xref_set_key(annot.xref, "AP", ap_val)
                                            add_log(f"Successfully applied vector shape '{base_shape}' to stamp {u['stamp_id']}")
                                        else:
                                            add_log(f"Shape '{base_shape}' had no vectors to apply.")
                                            
                                        # Delete the temporary page
                                        doc.delete_page(-1)
                                    except Exception as e:
                                        add_log(f"Error copying vectors for shape '{base_shape}': {e}")
                                        
                if pdf_changed:
                    add_log(f"Saving shape updates to PDF: {pdf_path}")
                    try:
                        doc.saveIncr()
                    except Exception:
                        # Fallback to saving to a temp file and replacing if incremental save fails
                        tmp_path = pdf_path + ".tmp"
                        doc.save(tmp_path, deflate=True)
                        os.replace(tmp_path, pdf_path)
                doc.close()
            except Exception as e:
                add_log(f"Failed to update shapes in PDF {pdf_path}: {e}")

        return jsonify({"success": True, "updated": changed, "stamps_evaluated": len(stamps), "logs": logs})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "logs": logs}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
