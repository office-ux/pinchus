import fitz
import json
import os
from detect_pencil import detect_elements, select_pdf_from_folder
import math
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════
#  CONFIG LOADER
# ═══════════════════════════════════════════════════════════════════

def load_config(config_path="config.json"):
    with open(config_path, "r") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════
#  GEOMETRY HELPERS
# ═══════════════════════════════════════════════════════════════════

def expand_rect(rect, margin):
    return fitz.Rect(rect.x0 - margin, rect.y0 - margin,
                     rect.x1 + margin, rect.y1 + margin)

def get_angle(p1, p2):
    return math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))

def normalize_angle(angle):
    angle = angle % 180
    if angle < 0:
        angle += 180
    return angle

def are_parallel(p1, p2, p3, p4, tolerance_degrees=20):
    angle1 = normalize_angle(get_angle(p1, p2))
    angle2 = normalize_angle(get_angle(p3, p4))
    diff = abs(angle1 - angle2)
    return diff <= tolerance_degrees or (180 - diff) <= tolerance_degrees

def are_perpendicular(p1, p2, p3, p4, tolerance_degrees=20):
    angle1 = normalize_angle(get_angle(p1, p2))
    angle2 = normalize_angle(get_angle(p3, p4))
    diff = abs(angle1 - angle2)
    return abs(diff - 90) <= tolerance_degrees or abs(diff - 270) <= tolerance_degrees

def point_to_line_dist(pt, line_p1, line_p2):
    num = abs((line_p2[0] - line_p1[0]) * (line_p1[1] - pt[1]) -
              (line_p1[0] - pt[0])       * (line_p2[1] - line_p1[1]))
    den = math.hypot(line_p2[0] - line_p1[0], line_p2[1] - line_p1[1])
    if den == 0:
        return math.hypot(pt[0] - line_p1[0], pt[1] - line_p1[1])
    return num / den

def distance_point_to_point(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def get_side(pt, line_p1, line_p2):
    return ((line_p2[0] - line_p1[0]) * (pt[1] - line_p1[1]) -
            (line_p2[1] - line_p1[1]) * (pt[0] - line_p1[0]))

def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])
    div = xdiff[0] * ydiff[1] - xdiff[1] * ydiff[0]
    if div == 0:
        return None
    d = (line1[0][0] * line1[1][1] - line1[0][1] * line1[1][0],
         line2[0][0] * line2[1][1] - line2[0][1] * line2[1][0])
    x = (d[0] * xdiff[1] - d[1] * xdiff[0]) / div
    y = (d[0] * ydiff[1] - d[1] * ydiff[0]) / div
    return x, y


# ═══════════════════════════════════════════════════════════════════
#  SNAPPING
# ═══════════════════════════════════════════════════════════════════

def project_point_onto_segment(pt, p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-10:
        return None
    t = ((pt[0] - p1[0]) * dx + (pt[1] - p1[1]) * dy) / seg_len_sq
    if 0.0 <= t <= 1.0:
        return (p1[0] + t * dx, p1[1] + t * dy)
    return None

def snap_polygon_to_pdf(polygon_pts, pdf_segments, snap_tolerance=6):
    snapped = []
    for pt in polygon_pts:
        best_dist = snap_tolerance
        best_proj = pt
        for seg in pdf_segments:
            if distance_point_to_point(seg[0], seg[1]) < 5:
                continue
            proj = project_point_onto_segment(pt, seg[0], seg[1])
            if proj is None:
                continue
            d = distance_point_to_point(pt, proj)
            if d < best_dist:
                best_dist = d
                best_proj = proj
        snapped.append(best_proj)
    return snapped


# ═══════════════════════════════════════════════════════════════════
#  CENTROID
# ═══════════════════════════════════════════════════════════════════

def polygon_centroid(pts):
    n = len(pts)
    if n == 0:
        return (0, 0)
    if n == 1:
        return pts[0]
    area = cx = cy = 0.0
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx   += (x0 + x1) * cross
        cy   += (y0 + y1) * cross
    area *= 0.5
    if abs(area) < 1e-10:
        return (sum(p[0] for p in pts) / n,
                sum(p[1] for p in pts) / n)
    return (cx / (6.0 * area), cy / (6.0 * area))


# ═══════════════════════════════════════════════════════════════════
#  EXTRACTION HELPERS
# ═══════════════════════════════════════════════════════════════════

def extract_pdf_segments(paths, excluded_rects=None, user_centerline_segments=None):
    """
    Extracts line segments from PDF paths, excluding any that are actually 
    the user's green marks.
    """
    def is_user_segment(seg):
        if not user_centerline_segments: return False
        for u_seg in user_centerline_segments:
            # Check if segment matches user mark (both directions)
            d1 = distance_point_to_point(seg[0], u_seg[0]) + distance_point_to_point(seg[1], u_seg[1])
            d2 = distance_point_to_point(seg[0], u_seg[1]) + distance_point_to_point(seg[1], u_seg[0])
            if d1 < 0.5 or d2 < 0.5: return True
        return False

    segments = []
    for path in paths:
        if excluded_rects:
            path_rect = path.get("rect")
            if path_rect:
                if any(path_rect.intersects(er) and 
                       abs(path_rect.width - er.width) < 1.0 and 
                       abs(path_rect.height - er.height) < 1.0 
                       for er in excluded_rects):
                    continue

        for item in path["items"]:
            if item[0] == "l":
                seg = (item[1], item[2])
                if not is_user_segment(seg):
                    segments.append(seg)
            elif item[0] == "re":
                r = item[1]
                rect_segs = [
                    ((r.x0, r.y0), (r.x1, r.y0)),
                    ((r.x1, r.y0), (r.x1, r.y1)),
                    ((r.x1, r.y1), (r.x0, r.y1)),
                    ((r.x0, r.y1), (r.x0, r.y0))
                ]
                for rs in rect_segs:
                    if not is_user_segment(rs):
                        segments.append(rs)
    return segments

def extract_user_segments(vertices):
    segments = []
    if not vertices:
        return segments
    for stroke in vertices:
        for i in range(len(stroke) - 1):
            p1, p2 = stroke[i], stroke[i + 1]
            if math.hypot(p2[0] - p1[0], p2[1] - p1[1]) > 5:
                segments.append((p1, p2))
    return segments


# ═══════════════════════════════════════════════════════════════════
#  CENTERLINE PROCESSING
# ═══════════════════════════════════════════════════════════════════

def rdp_simplify(points, epsilon):
    if len(points) < 3:
        return points
    dmax, index = 0.0, 0
    end = len(points) - 1
    for i in range(1, end):
        d = point_to_line_dist(points[i], points[0], points[end])
        if d > dmax:
            index, dmax = i, d
    if dmax > epsilon:
        return rdp_simplify(points[:index + 1], epsilon)[:-1] + \
               rdp_simplify(points[index:], epsilon)
    return [points[0], points[end]]

def decimate_points(points, dist_tolerance=5):
    if len(points) < 3:
        return points
    result = [points[0]]
    for pt in points[1:-1]:
        if distance_point_to_point(result[-1], pt) > dist_tolerance:
            result.append(pt)
    result.append(points[-1])
    return result


# ═══════════════════════════════════════════════════════════════════
#  GRAPH CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════

def build_segment_graph(pdf_segments, snap_dist=4):
    def snap_key(pt):
        return (round(pt[0] / snap_dist) * snap_dist,
                round(pt[1] / snap_dist) * snap_dist)
    graph = defaultdict(list)
    for i, seg in enumerate(pdf_segments):
        graph[snap_key(seg[0])].append(i)
        graph[snap_key(seg[1])].append(i)
    return graph, snap_key

def find_wall_seed(centerline_pts, pdf_segments, side,
                   max_dist=60, min_seg_len=12, min_wall_dist=3.0):
    best_idx  = None
    best_dist = float('inf')
    for i in range(len(centerline_pts) - 1):
        cl_p1, cl_p2 = centerline_pts[i], centerline_pts[i + 1]
        for j, seg in enumerate(pdf_segments):
            if distance_point_to_point(seg[0], seg[1]) < min_seg_len:
                continue
            if not are_parallel(cl_p1, cl_p2, seg[0], seg[1],
                                 tolerance_degrees=15):
                continue
            dist = point_to_line_dist(seg[0], cl_p1, cl_p2)
            # Use a slightly stricter lower bound to ensure we are not on the user's line
            if not (max(min_wall_dist, 0.5) < dist < max_dist):
                continue
            seg_side = get_side(seg[0], cl_p1, cl_p2)
            correct  = (side > 0 and seg_side > 0) or \
                       (side < 0 and seg_side < 0)
            if correct and dist < best_dist:
                best_dist = dist
                best_idx  = j
    return best_idx


# ═══════════════════════════════════════════════════════════════════
#  GRAPH WALK
# ═══════════════════════════════════════════════════════════════════

def walk_wall(seed_idx, pdf_segments, graph, snap_key,
              centerline_pts, cfg_walk):
    if seed_idx is None:
        return None

    max_steps        = int(cfg_walk["max_steps"])
    deviation_margin = cfg_walk["deviation_margin"]
    par_tol          = cfg_walk["par_tolerance_deg"]
    perp_tol         = cfg_walk["perp_tolerance_deg"]
    only_straight    = cfg_walk.get("only_straight", False)

    seed_seg = pdf_segments[seed_idx]
    visited  = {seed_idx}

    cl_start = centerline_pts[0]
    cl_end   = centerline_pts[-1]
    
    # Longitudinal vector for the whole stroke
    v_total = (cl_end[0] - cl_start[0], cl_end[1] - cl_start[1])
    L2 = v_total[0]**2 + v_total[1]**2

    d0 = distance_point_to_point(seed_seg[0], cl_start)
    d1 = distance_point_to_point(seed_seg[1], cl_start)
    if d0 <= d1:
        path, current_end = [seed_seg[0], seed_seg[1]], seed_seg[1]
    else:
        path, current_end = [seed_seg[1], seed_seg[0]], seed_seg[0]

    current_dir = (path[-2], path[-1])
    primary_dir = current_dir

    cl_xs = [p[0] for p in centerline_pts]
    cl_ys = [p[1] for p in centerline_pts]
    bbox  = (min(cl_xs) - deviation_margin, min(cl_ys) - deviation_margin,
             max(cl_xs) + deviation_margin, max(cl_ys) + deviation_margin)

    for step in range(max_steps):
        key        = snap_key(current_end)
        candidates = graph.get(key, [])
        best_score = best_next_idx = best_far_end = None

        for seg_idx in candidates:
            if seg_idx in visited:
                continue
            seg     = pdf_segments[seg_idx]
            seg_len = distance_point_to_point(seg[0], seg[1])
            if seg_len < 5:
                continue

            is_par_primary  = are_parallel(
                primary_dir[0], primary_dir[1], seg[0], seg[1], par_tol)
            is_par_current  = are_parallel(
                current_dir[0], current_dir[1], seg[0], seg[1], par_tol)
            is_perp_current = are_perpendicular(
                current_dir[0], current_dir[1], seg[0], seg[1], perp_tol)

            if only_straight and is_perp_current:
                continue

            if not (is_par_primary or is_par_current or is_perp_current):
                continue

            far_end = seg[1] if distance_point_to_point(seg[0], current_end) \
                              <= distance_point_to_point(seg[1], current_end) \
                             else seg[0]

            if not (bbox[0] <= far_end[0] <= bbox[2] and
                    bbox[1] <= far_end[1] <= bbox[3]):
                continue
            
            # Longitudinal check: don't walk past the stroke ends
            if L2 > 0:
                # Projection parameter t along the stroke vector
                t = ((far_end[0] - cl_start[0]) * v_total[0] + 
                     (far_end[1] - cl_start[1]) * v_total[1]) / L2
                # Allow a small buffer (e.g., 10 points) past the ends
                buffer_t = 10.0 / math.sqrt(L2)
                if t < -buffer_t or t > 1.0 + buffer_t:
                    continue

            priority = 0 if is_par_primary else (1 if is_par_current else 2)
            score    = (priority, -seg_len)
            if best_score is None or score < best_score:
                best_score, best_next_idx, best_far_end = score, seg_idx, far_end

        if best_next_idx is None:
            print(f"    Walk stopped at step {step} — no continuation.")
            break

        visited.add(best_next_idx)
        next_seg = pdf_segments[best_next_idx]
        new_dir  = (next_seg[0], next_seg[1]) \
                   if distance_point_to_point(next_seg[0], current_end) \
                   <= distance_point_to_point(next_seg[1], current_end) \
                   else (next_seg[1], next_seg[0])

        current_dir = new_dir
        if not are_perpendicular(primary_dir[0], primary_dir[1],
                                 new_dir[0],     new_dir[1], perp_tol):
            primary_dir = current_dir

        path.append(best_far_end)
        current_end = best_far_end

    return path


# ═══════════════════════════════════════════════════════════════════
#  POLYGON CLOSING
# ═══════════════════════════════════════════════════════════════════

def close_polygon_with_caps(left_path, right_path, pdf_segments, simplified_cl):
    def find_cap(wall_end, direction_seg, search_radius=30):
        best, best_d = None, float('inf')
        for seg in pdf_segments:
            if distance_point_to_point(seg[0], seg[1]) < 5:
                continue
            if not are_perpendicular(direction_seg[0], direction_seg[1],
                                     seg[0], seg[1], tolerance_degrees=20):
                continue
            d = min(distance_point_to_point(wall_end, seg[0]),
                    distance_point_to_point(wall_end, seg[1]))
            if d < search_radius and d < best_d:
                best_d, best = d, seg
        return best

    start_dir = (simplified_cl[0], simplified_cl[1])
    s_cap = find_cap(left_path[0], start_dir)
    if s_cap:
        sl = line_intersection(s_cap, (left_path[0],  left_path[1]))
        sr = line_intersection(s_cap, (right_path[0], right_path[1]))
        if sl: left_path[0]  = sl
        if sr: right_path[0] = sr

    end_dir = (simplified_cl[-2], simplified_cl[-1])
    e_cap = find_cap(left_path[-1], end_dir)
    if e_cap:
        el = line_intersection(e_cap, (left_path[-2], left_path[-1]))
        er = line_intersection(e_cap, (right_path[-2], right_path[-1]))
        if el: left_path[-1]  = el
        if er: right_path[-1] = er

    polygon = left_path + list(reversed(right_path))
    return [(round(p[0], 2), round(p[1], 2)) for p in polygon]


# ═══════════════════════════════════════════════════════════════════
#  STRAIGHT LINE CONSENSUS (SURVEY)
# ═══════════════════════════════════════════════════════════════════

def survey_straight_walls(centerline_pts, pdf_segments, cfg_search, cfg_walk):
    """
    Probes the CAD geometry at specific intervals along the stroke.
    Each probe 'votes' for its closest physical CAD line.
    The wall is placed at the physical distance with the most votes.
    """
    if len(centerline_pts) < 2: return None, None
    
    p1, p2 = centerline_pts[0], centerline_pts[-1]
    max_dist = cfg_search["wall_max_dist"]
    min_dist = max(cfg_search["min_wall_dist"], 0.5) # Hard safety floor
    par_tol  = cfg_walk["par_tolerance_deg"]
    interval = cfg_walk.get("sampling_interval", 10.0)
    
    # Calculate stroke vector and length
    v = (p2[0]-p1[0], p2[1]-p1[1])
    L = math.hypot(v[0], v[1])
    if L == 0: return None, None
    u = (v[0]/L, v[1]/L) # Unit vector along stroke
    perp = (-u[1], u[0]) # Perpendicular unit vector (Left side)

    # Storage for votes (Physical Distance -> Count)
    votes = {+1: defaultdict(int), -1: defaultdict(int)}
    # Map from rounded key to a list of exact physical distances
    samples = {+1: defaultdict(list), -1: defaultdict(list)}
    
    # Perform Probing at Intervals
    num_steps = max(2, int(L / interval) + 1)
    for i in range(num_steps):
        t = i / (num_steps - 1)
        probe_pt = (p1[0] + v[0] * t, p1[1] + v[1] * t)
        
        # Find closest physical line on Left and Right at this specific probe point
        closest = {+1: {"dist": float('inf'), "val": None}, 
                   -1: {"dist": float('inf'), "val": None}}
        
        for seg in pdf_segments:
            # Must be parallel
            if not are_parallel(p1, p2, seg[0], seg[1], par_tol):
                continue
            
            # Distance from probe point to this CAD line
            dist_to_line = point_to_line_dist(probe_pt, seg[0], seg[1])
            
            # Must be within bounds
            if not (min_dist < dist_to_line < max_dist):
                continue
                
            side = 1 if get_side(probe_pt, seg[0], seg[1]) < 0 else -1 # Side relative to CAD line
            # Wait, get_side is (pt, line_p1, line_p2). 
            # We want side of CAD line relative to our stroke
            side = 1 if get_side(seg[0], p1, p2) > 0 else -1
            
            if dist_to_line < closest[side]["dist"]:
                closest[side]["dist"] = dist_to_line
                closest[side]["val"] = dist_to_line

        # Record the 'vote' for this probe point
        for side in [+1, -1]:
            val = closest[side]["val"]
            if val is not None:
                # Group by 0.5 point resolution
                key = round(val * 2) / 2.0
                votes[side][key] += 1
                samples[side][key].append(val)

    def get_consensus_wall(side_votes, side_samples, side_val):
        if not side_votes: return None, []
        # The key with the most votes wins
        best_key = max(side_votes, key=side_votes.get)
        
        # Use the average of the REAL physical distances that voted for this key
        real_physical_dist = sum(side_samples[best_key]) / len(side_samples[best_key])
        
        # side=1: left ( -uy, ux ), side=-1: right ( uy, -ux )
        off_x, off_y = (perp[0], perp[1]) if side_val == 1 else (-perp[0], -perp[1])
        
        # Construct the final wall line (start and end)
        wall_line = [
            (p1[0] + off_x * real_physical_dist, p1[1] + off_y * real_physical_dist),
            (p2[0] + off_x * real_physical_dist, p2[1] + off_y * real_physical_dist)
        ]
        
        # Also return all points that actually contributed to this wall for debug visualization
        # We project each sample distance back onto its respective probe point location later
        # But for now, we'll just return a placeholder list to indicate success points
        # Actually, let's return the probe points themselves shifted by the physical dist
        points_sampled = []
        num_steps = max(2, int(L / interval) + 1)
        for i in range(num_steps):
            t = i / (num_steps - 1)
            probe_pt = (p1[0] + v[0] * t, p1[1] + v[1] * t)
            points_sampled.append((probe_pt[0] + off_x * real_physical_dist, 
                                   probe_pt[1] + off_y * real_physical_dist))

        return wall_line, points_sampled

    left_path, left_debug  = get_consensus_wall(votes[+1], samples[+1], +1)
    right_path, right_debug = get_consensus_wall(votes[-1], samples[-1], -1)
    
    return left_path, right_path, left_debug, right_debug


# ═══════════════════════════════════════════════════════════════════
#  WALK QUALITY CHECK
# ═══════════════════════════════════════════════════════════════════

def walk_is_usable(path, centerline_pts, min_coverage=0.5):
    if path is None or len(path) < 2:
        return False
    cl_xs = [p[0] for p in centerline_pts]
    cl_ys = [p[1] for p in centerline_pts]
    cl_diag = math.hypot(max(cl_xs) - min(cl_xs), max(cl_ys) - min(cl_ys))
    if cl_diag < 1:
        return False
    walk_diag = math.hypot(
        max(p[0] for p in path) - min(p[0] for p in path),
        max(p[1] for p in path) - min(p[1] for p in path))
    return (walk_diag / cl_diag) >= min_coverage


# ═══════════════════════════════════════════════════════════════════
#  SOLUTION 1 FALLBACK
# ═══════════════════════════════════════════════════════════════════

def sample_width_at_point(pt, direction_seg, pdf_segments, max_dist=60, par_tol=20, min_wall_dist=3.0):
    left_d = right_d = float('inf')
    for p_seg in pdf_segments:
        if distance_point_to_point(p_seg[0], p_seg[1]) < 10:
            continue
        if not are_parallel(direction_seg[0], direction_seg[1],
                            p_seg[0], p_seg[1], tolerance_degrees=par_tol):
            continue
        dist = point_to_line_dist(pt, p_seg[0], p_seg[1])
        if min_wall_dist < dist < max_dist:
            side = get_side(p_seg[0], direction_seg[0], direction_seg[1])
            if side > 0: left_d  = min(left_d,  dist)
            else:        right_d = min(right_d, dist)
    
    # If no wall is found, use the full max_dist as the fallback
    fallback = max_dist
    left_d  = left_d  if left_d  != float('inf') else fallback
    right_d = right_d if right_d != float('inf') else fallback
    return left_d, right_d

def offset_polyline_variable(vertices, pdf_segments, max_dist, par_tol, min_wall_dist):
    if len(vertices) < 2:
        return list(vertices), list(vertices)
    left_pts, right_pts = [], []
    for i, pt in enumerate(vertices):
        seg = (vertices[i], vertices[i+1]) if i < len(vertices)-1 \
              else (vertices[i-1], vertices[i])
        lw, rw = sample_width_at_point(pt, seg, pdf_segments, max_dist, par_tol, min_wall_dist)
        v = (seg[1][0]-seg[0][0], seg[1][1]-seg[0][1])
        L = math.hypot(v[0], v[1])
        if L == 0:
            left_pts.append(pt); right_pts.append(pt); continue
        u  = (v[0]/L, v[1]/L)
        left_pts.append( (pt[0] + (-u[1])*lw, pt[1] + u[0]*lw) )
        right_pts.append((pt[0] +   u[1]*rw,  pt[1] + (-u[0])*rw) )
    return left_pts, right_pts


# ═══════════════════════════════════════════════════════════════════
#  MAIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def analyze_boundaries(pdf_path, target_subjects, output_path, cfg):
    cfg_search = cfg["search"]
    cfg_graph  = cfg["graph"]
    cfg_walk   = cfg["walk"]
    cfg_debug  = cfg["debug"]
    cfg_label  = cfg["label"]

    print(f"Analyzing boundaries in {pdf_path}...")
    doc = fitz.open(pdf_path)

    elements = detect_elements(pdf_path, target_subjects)
    if not elements:
        print("No user centerlines found.")
        return

    for idx, el in enumerate(elements):
        page_num = el['page'] - 1
        page     = doc[page_num]

        original_rect = fitz.Rect(el['rect'])
        search_rect   = expand_rect(original_rect,
                                    margin=cfg_search["search_rect_margin"])

        print(f"\n{'═'*55}")
        print(f"Element {idx+1}: {el['subject']}")
        print(f"{'═'*55}")

        drawings = page.get_drawings()
        relevant_drawings = [
            p for p in drawings
            if p.get("rect") and search_rect.intersects(p["rect"])
        ]
        
        user_segments = extract_user_segments(el.get("vertices"))
        if not user_segments:
            print("  No valid user segments. Skipping.")
            continue

        # Collect all user annotation rects on this page to exclude them from detection
        user_annots = [fitz.Rect(a.rect) for a in page.annots()]
        # Physical Exclusion: Purge any line segment that matches the user's pencil stroke coordinates
        pdf_segments = extract_pdf_segments(relevant_drawings, 
                                            excluded_rects=user_annots,
                                            user_centerline_segments=user_segments)

        raw_pts    = [user_segments[0][0]] + [s[1] for s in user_segments]
        decimated  = decimate_points(raw_pts, dist_tolerance=3)
        
        # ── NORMALIZE STROKE (Straighten or Smooth) ─────────────────────
        if cfg_walk.get("only_straight", False):
            # Force to a single straight line from start to end
            simplified = [raw_pts[0], raw_pts[-1]]
        else:
            # Smoothly preserve turns and straight lines
            simplified = rdp_simplify(decimated, epsilon=2)

        # ── VISUAL REWRITE (Replace messy mark with clean version) ──────
        rewrite_done = False
        for a in page.annots():
            if a.info.get("id") == el["id"]:
                try:
                    # Capture the metadata from the old mark
                    old_info = a.info
                    
                    # Add a new, clean green mark using the simplified points
                    # Using add_polyline_annot for "Straight" lines ensures they are crisp
                    if cfg_walk.get("only_straight", False):
                        new_a = page.add_polyline_annot(simplified)
                    else:
                        new_a = page.add_ink_annot([simplified])
                    
                    new_a.set_colors(stroke=(0, 1, 0)) # Green
                    new_a.set_info(old_info)
                    new_a.update()
                    
                    # Delete the original messy pencil mark
                    page.delete_annot(a)
                    
                    rewrite_done = True
                except Exception as e:
                    print(f"    (Note: Visual rewrite of stroke failed: {e})")
                break
        
        if rewrite_done:
            print(f"  ✓ Pencil mark rewritten ({'Straight' if cfg_walk.get('only_straight') else 'Smoothed'})")
        else:
            print("  ⚠ Could not find original pencil mark to rewrite.")

        print(f"  Centerline: {len(raw_pts)} raw → {len(decimated)} "
              f"decimated → {len(simplified)} after Normalization")

        graph, snap_key = build_segment_graph(
            pdf_segments, snap_dist=cfg_graph["graph_snap_dist"])
        print(f"  Graph nodes: {len(graph)}  PDF segments: {len(pdf_segments)}")

        left_seed_idx  = find_wall_seed(
            simplified, pdf_segments, side=+1,
            max_dist=cfg_search["wall_max_dist"],
            min_seg_len=cfg_search["min_seg_len"],
            min_wall_dist=cfg_search["min_wall_dist"])
        right_seed_idx = find_wall_seed(
            simplified, pdf_segments, side=-1,
            max_dist=cfg_search["wall_max_dist"],
            min_seg_len=cfg_search["min_seg_len"],
            min_wall_dist=cfg_search["min_wall_dist"])

        print(f"  Left  seed: {left_seed_idx} "
              f"({'found' if left_seed_idx  is not None else 'NOT FOUND'})")
        print(f"  Right seed: {right_seed_idx} "
              f"({'found' if right_seed_idx is not None else 'NOT FOUND'})")

        if cfg_walk.get("only_straight", False):
            print("  Performing Straight-Line Consensus Survey...")
            left_path, right_path, left_debug, right_debug = survey_straight_walls(
                simplified, pdf_segments, cfg_search, cfg_walk)
            # For debug drawing in straight mode, use the full list of interval points
            debug_left_path = left_debug
            debug_right_path = right_debug
        else:
            left_path  = walk_wall(left_seed_idx,  pdf_segments, graph,
                                   snap_key, simplified, cfg_walk)
            right_path = walk_wall(right_seed_idx, pdf_segments, graph,
                                   snap_key, simplified, cfg_walk)
            # For traditional walk, debug drawing uses the walk path itself
            debug_left_path = left_path
            debug_right_path = right_path

        min_cov  = cfg_walk["min_coverage"]
        left_ok  = walk_is_usable(left_path,  simplified, min_cov)
        right_ok = walk_is_usable(right_path, simplified, min_cov)

        print(f"  Left  wall: "
              f"{len(left_path)  if left_path  else 0} pts "
              f"({'OK' if left_ok  else 'INSUFFICIENT'})")
        print(f"  Right wall: "
              f"{len(right_path) if right_path else 0} pts "
              f"({'OK' if right_ok else 'INSUFFICIENT'})")

        # ── DEBUG dots (now numbers) ─────────────────────────────────────
        if cfg_debug["show_walk_dots"] and output_path:
            label_str = str(idx + 1)
            for walk_path, color in [
                (debug_left_path,  tuple(cfg_debug["left_dot_color"])),
                (debug_right_path, tuple(cfg_debug["right_dot_color"])),
            ]:
                if walk_path:
                    fs_debug = 6  # Small font for debug numbers
                    for pt in walk_path:
                        tw = fitz.get_text_length(label_str, fontsize=fs_debug)
                        # Center the text rect on the point
                        text_rect = fitz.Rect(pt[0] - tw/2, pt[1] - fs_debug/2,
                                              pt[0] + tw/2, pt[1] + fs_debug/2)
                        
                        num_annot = page.add_freetext_annot(
                            text_rect, label_str,
                            fontsize=fs_debug,
                            text_color=color,
                            fill_color=None  # Transparent background
                        )
                        num_annot.set_info(subject="Walk debug")
                        num_annot.update()

        # ── Build polygon ────────────────────────────────────────────────
        if left_ok and right_ok:
            print("  ✓ Using Solution 2 (graph-walk)")
            final_polygon = close_polygon_with_caps(
                left_path, right_path, pdf_segments, simplified)
            final_polygon = snap_polygon_to_pdf(
                final_polygon, pdf_segments,
                snap_tolerance=cfg_graph["snap_tolerance"])
            print(f"  Polygon after snap: {len(final_polygon)} vertices")

        else:
            print("  ⚠ Falling back to Solution 1 (per-vertex offset)")
            left_poly, right_poly = offset_polyline_variable(
                simplified, pdf_segments,
                max_dist=cfg_search["wall_max_dist"],
                par_tol=cfg_walk["par_tolerance_deg"],
                min_wall_dist=cfg_search["min_wall_dist"])

            start_dir = (simplified[0],  simplified[1])
            end_dir   = (simplified[-2], simplified[-1])

            def snap_to_cap(wall, cap_dir, which_end):
                ia, ib = (0, 1) if which_end == 'start' else (-1, -2)
                ep = wall[ia]
                for seg in pdf_segments:
                    if distance_point_to_point(seg[0], seg[1]) < 5:
                        continue
                    if not are_perpendicular(cap_dir[0], cap_dir[1],
                                            seg[0], seg[1], cfg_walk["perp_tolerance_deg"]):
                        continue
                    d = min(distance_point_to_point(ep, seg[0]),
                            distance_point_to_point(ep, seg[1]))
                    if d < 30:
                        snapped = line_intersection(seg, (wall[ia], wall[ib]))
                        if snapped:
                            wall[ia] = snapped
                        return

            snap_to_cap(left_poly,  start_dir, 'start')
            snap_to_cap(right_poly, start_dir, 'start')
            snap_to_cap(left_poly,  end_dir,   'end')
            snap_to_cap(right_poly, end_dir,   'end')

            final_polygon = left_poly + list(reversed(right_poly))
            final_polygon = [(round(p[0], 2), round(p[1], 2))
                             for p in final_polygon]

        print(f"  Final polygon: {len(final_polygon)} vertices")

        if output_path:
            annot = page.add_polygon_annot(final_polygon)
            annot.set_colors(stroke=(0, 0, 1))
            annot.set_info(subject=f"{el['subject']} Boundary")
            annot.update()

            label     = str(idx + 1)
            cx, cy    = polygon_centroid(final_polygon)
            fs        = cfg_label["font_size"]
            text_w    = fitz.get_text_length(label, fontsize=fs)
            text_rect = fitz.Rect(cx - text_w/2 - 2, cy - fs,
                                  cx + text_w/2 + 2, cy + 2)
            la = page.add_freetext_annot(
                text_rect, label,
                fontsize   = fs,
                text_color = tuple(cfg_label["text_color"]),
                fill_color = tuple(cfg_label["fill_color"]),
            )
            la.set_info(subject=f"{el['subject']} Label")
            la.update()
            print(f"  Label '{label}' placed at ({cx:.1f}, {cy:.1f})")

    if output_path:
        doc.save(output_path)
        print(f"\nSaved to: {output_path}")


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    cfg = load_config("config.json")

    pdf_file = select_pdf_from_folder(cfg["paths"]["input_folder"])

    if pdf_file:
        out_dir = cfg["paths"]["output_folder"]
        os.makedirs(out_dir, exist_ok=True)

        base_name = os.path.basename(pdf_file).replace(".pdf", "_analyzed.pdf")
        out_file  = os.path.join(out_dir, base_name)

        analyze_boundaries(
            pdf_file,
            cfg["targets"],
            output_path=out_file,
            cfg=cfg,
        )

        print(f"\nOpening {out_file}...")
        try:
            os.startfile(out_file)
        except AttributeError:
            import subprocess
            subprocess.run(['start', '', out_file], shell=True)