import math
import os
import multiprocessing
from collections import defaultdict

import fitz

import detect_matching_lines as matching_lines
import detect_subject_items as subject_items
import detect_patterns_output


def rotate_rel_point(p, angle):
    """Rotate a relative point by 0, 90, 180, or 270 degrees."""
    x, y = p
    if angle == 90:
        return (-y, x)
    if angle == 180:
        return (-x, -y)
    if angle == 270:
        return (y, -x)
    return (x, y)


def get_unique_signatures(subject_matches):
    signatures = []
    seen_keys = set()

    for item in subject_matches:
        target = item["target"]
        raw_segments = item.get("segments", [])
        if not raw_segments:
            continue

        # First pass: find all rect bounds in the stamp
        rect_bounds_list = []
        for seg in raw_segments:
            if seg.get("shape_type") == "rect":
                if "x" in seg and "y" in seg and "width" in seg and "height" in seg:
                    w = abs(seg["width"])
                    h = abs(seg["height"])
                    x = min(seg["x"], seg["x"] + seg["width"])
                    y = min(seg["y"], seg["y"] + seg["height"])
                else:
                    w = abs(seg["end"][0] - seg["start"][0])
                    h = abs(seg["end"][1] - seg["start"][1])
                    x = min(seg["start"][0], seg["end"][0])
                    y = min(seg["start"][1], seg["end"][1])
                rect_bounds_list.append((x, y, x + w, y + h))

        segments = []
        for seg in raw_segments:
            stype = seg.get("shape_type", "line")
            weight = seg.get("effective_line_weight", seg.get("line_weight", 1.0))
            color = seg.get("stroke_color", (0,0,0))
            
            if stype == "rect":
                if "x" in seg and "y" in seg and "width" in seg and "height" in seg:
                    w = abs(seg["width"])
                    h = abs(seg["height"])
                    x = min(seg["x"], seg["x"] + seg["width"])
                    y = min(seg["y"], seg["y"] + seg["height"])
                else:
                    w = abs(seg["end"][0] - seg["start"][0])
                    h = abs(seg["end"][1] - seg["start"][1])
                    x = min(seg["start"][0], seg["end"][0])
                    y = min(seg["start"][1], seg["end"][1])
                
                # Explode rect into 4 line segments
                pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
                for i in range(4):
                    p_start = pts[i]
                    p_end = pts[(i + 1) % 4]
                    segments.append({
                        "shape_type": "line",
                        "start": p_start,
                        "end": p_end,
                        "length": matching_lines.dist(p_start, p_end),
                        "line_weight": weight,
                        "stroke_color": color
                    })
            elif stype == "line":
                # Check if this line is a diagonal of any rect in rect_bounds_list
                is_diagonal = False
                p1 = seg["start"]
                p2 = seg["end"]
                tol = 1.5
                
                def pt_near(pt, target):
                    return abs(pt[0] - target[0]) < tol and abs(pt[1] - target[1]) < tol
                
                for rx0, ry0, rx1, ry1 in rect_bounds_list:
                    d1_fwd = pt_near(p1, (rx0, ry0)) and pt_near(p2, (rx1, ry1))
                    d1_rev = pt_near(p2, (rx0, ry0)) and pt_near(p1, (rx1, ry1))
                    d2_fwd = pt_near(p1, (rx1, ry0)) and pt_near(p2, (rx0, ry1))
                    d2_rev = pt_near(p2, (rx1, ry0)) and pt_near(p1, (rx0, ry1))
                    
                    if d1_fwd or d1_rev or d2_fwd or d2_rev:
                        is_diagonal = True
                        break
                
                if not is_diagonal:
                    segments.append(seg)
            else:
                segments.append(seg)
                
        if not segments:
            continue

        base_x, base_y = segments[0]["start"]
        
        annot_rect = item.get("rect")
        if annot_rect is not None:
            try:
                annot_w = abs(float(annot_rect[2]) - float(annot_rect[0]))
                annot_h = abs(float(annot_rect[3]) - float(annot_rect[1]))
            except Exception:
                annot_w = annot_h = 0.0
        else:
            annot_w = annot_h = 0.0
        
        rel_segments = []
        for seg in segments:
            shape_type = seg.get("shape_type", "line")
            base = {
                "length": seg["length"],
                "line_weight": seg.get("effective_line_weight", seg["line_weight"]),
                "stroke_color": seg["stroke_color"],
                "shape_type": shape_type
            }
            if shape_type == "arc":
                pts = seg["points"]
                base["points_rel"] = [(p[0] - base_x, p[1] - base_y) for p in pts]
                base["start_rel"] = (pts[0][0] - base_x, pts[0][1] - base_y)
                base["end_rel"] = (pts[3][0] - base_x, pts[3][1] - base_y)
            elif shape_type == "rect":
                base["start_rel"] = (seg["start"][0] - base_x, seg["start"][1] - base_y)
                base["end_rel"] = (seg["end"][0] - base_x, seg["end"][1] - base_y)
                base["width"] = seg["width"]
                base["height"] = seg["height"]
            else:
                base["start_rel"] = (seg["start"][0] - base_x, seg["start"][1] - base_y)
                base["end_rel"] = (seg["end"][0] - base_x, seg["end"][1] - base_y)
            rel_segments.append(base)
        
        sig_key_parts = []
        for s in rel_segments:
            sig_key_parts.append((
                round(s["start_rel"][0], 2), round(s["start_rel"][1], 2),
                round(s["end_rel"][0], 2), round(s["end_rel"][1], 2),
                round(s["length"], 2),
                round(s["line_weight"], 2),
                tuple(round(c, 3) for c in (s["stroke_color"] or [])),
                s["shape_type"]
            ))
        sig_key = (target, tuple(sorted(sig_key_parts)))

        if sig_key not in seen_keys:
            seen_keys.add(sig_key)
            for angle in [0, 90, 180, 270]:
                temp_segs = []
                for s in rel_segments:
                    new_s = {
                        "shape_type": s["shape_type"],
                        "start_rel": rotate_rel_point(s["start_rel"], angle),
                        "end_rel": rotate_rel_point(s["end_rel"], angle),
                        "length": s["length"],
                        "line_weight": s["line_weight"],
                        "stroke_color": s["stroke_color"]
                    }
                    if s["shape_type"] == "arc":
                        new_s["points_rel"] = [rotate_rel_point(p, angle) for p in s.get("points_rel", [])]
                    elif s["shape_type"] == "rect":
                        if angle in [90, 270]:
                            new_s["width"] = s["height"]
                            new_s["height"] = s["width"]
                        else:
                            new_s["width"] = s["width"]
                            new_s["height"] = s["height"]
                    temp_segs.append(new_s)
                
                rx, ry = temp_segs[0]["start_rel"]
                for s in temp_segs:
                    s["start_rel"] = (s["start_rel"][0] - rx, s["start_rel"][1] - ry)
                    s["end_rel"] = (s["end_rel"][0] - rx, s["end_rel"][1] - ry)
                    if s["shape_type"] == "arc":
                        s["points_rel"] = [(p[0] - rx, p[1] - ry) for p in s.get("points_rel", [])]
                
                xs = [s["start_rel"][0] for s in temp_segs] + [s["end_rel"][0] for s in temp_segs]
                ys = [s["start_rel"][1] for s in temp_segs] + [s["end_rel"][1] for s in temp_segs]
                
                seg_weights = [s["line_weight"] for s in temp_segs]
                match_weight = sum(seg_weights) / len(seg_weights) if seg_weights else 0.0

                signatures.append({
                    "target": target,
                    "type": item.get("type"),
                    "segments": temp_segs,
                    "width": max(xs) - min(xs) if xs else 0,
                    "height": max(ys) - min(ys) if ys else 0,
                    "annot_width": annot_w if angle in [0, 180] else annot_h,
                    "annot_height": annot_h if angle in [0, 180] else annot_w,
                    "angle": angle,
                    "match_line_weight": match_weight,
                    "stroke_color": temp_segs[0]["stroke_color"] if temp_segs else (0,0,0)
                })
            
    return signatures


def iter_page_items(page, box_dims=None, len_tol=1.0):
    for drawing_index, drawing in enumerate(page.get_drawings()):
        line_weight = float(drawing.get("width") or 1.0)
        
        stroke_color = drawing.get("color")
        fill_color = drawing.get("fill")
        if stroke_color is None and fill_color is not None:
            stroke_color = fill_color
        elif stroke_color is None:
            stroke_color = (0, 0, 0)
        
        for item_index, item in enumerate(drawing["items"]):
            source_lbl = f"drawing {drawing_index}, item {item_index}"
            if item[0] == "l":
                start = item[1]
                end = item[2]
                yield {
                    "source": source_lbl,
                    "shape_type": "line",
                    "start": (start[0], start[1]),
                    "end": (end[0], end[1]),
                    "length": matching_lines.dist(start, end),
                    "line_weight": line_weight,
                    "stroke_color": stroke_color,
                }
            elif item[0] == "re":
                rect = item[1]
                w = abs(rect.x1 - rect.x0)
                h = abs(rect.y1 - rect.y0)
                x = min(rect.x0, rect.x1)
                y = min(rect.y0, rect.y1)
                
                # Check if this rect matches any signature dimensions
                should_explode = False
                if box_dims:
                    for bw, bh in box_dims:
                        if (abs(w - bw) <= len_tol and abs(h - bh) <= len_tol) or \
                           (abs(w - bh) <= len_tol and abs(h - bw) <= len_tol):
                            should_explode = True
                            break
                else:
                    should_explode = True
                
                if should_explode:
                    yield from explode_rect_to_lines(x, y, w, h, line_weight, stroke_color, source_lbl)
                else:
                    # Skip completely to save memory and time
                    pass
            elif item[0] == "qu":
                quad = item[1]
                pts = [(quad.ul.x, quad.ul.y), (quad.ur.x, quad.ur.y), (quad.lr.x, quad.lr.y), (quad.ll.x, quad.ll.y)]
                
                # Check if quad bounding box matches any signature dimensions
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                qw = max(xs) - min(xs)
                qh = max(ys) - min(ys)
                
                should_explode = False
                if box_dims:
                    for bw, bh in box_dims:
                        if (abs(qw - bw) <= len_tol and abs(qh - bh) <= len_tol) or \
                           (abs(qw - bh) <= len_tol and abs(qh - bw) <= len_tol):
                            should_explode = True
                            break
                else:
                    should_explode = True
                
                if should_explode:
                    yield from explode_polygon_to_lines(pts, line_weight, stroke_color, source_lbl)
                else:
                    # Skip completely
                    pass
            elif item[0] == "c":
                p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                pts = [(p1.x, p1.y), (p2.x, p2.y), (p3.x, p3.y), (p4.x, p4.y)]
                chord = matching_lines.dist(pts[0], pts[3])
                hull = (matching_lines.dist(pts[0], pts[1]) + 
                        matching_lines.dist(pts[1], pts[2]) + 
                        matching_lines.dist(pts[2], pts[3]))
                yield {
                    "source": source_lbl,
                    "shape_type": "arc",
                    "points": pts,
                    "start": pts[0],
                    "end": pts[3],
                    "length": (chord + hull) / 2,
                    "line_weight": line_weight,
                    "stroke_color": stroke_color,
                }


def explode_rect_to_lines(x, y, w, h, line_weight, stroke_color, source=""):
    x0, x1 = min(x, x + w), max(x, x + w)
    y0, y1 = min(y, y + h), max(y, y + h)
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    lines = []
    for i in range(4):
        p_start = pts[i]
        p_end = pts[(i + 1) % 4]
        lines.append({
            "source": source,
            "shape_type": "line",
            "start": p_start,
            "end": p_end,
            "length": matching_lines.dist(p_start, p_end),
            "line_weight": line_weight,
            "effective_line_weight": line_weight,
            "stroke_color": stroke_color
        })
    return lines

def explode_polygon_to_lines(pts, line_weight, stroke_color, source=""):
    lines = []
    n = len(pts)
    for i in range(n):
        p_start = pts[i]
        p_end = pts[(i + 1) % n]
        lines.append({
            "source": source,
            "shape_type": "line",
            "start": p_start,
            "end": p_end,
            "length": matching_lines.dist(p_start, p_end),
            "line_weight": line_weight,
            "effective_line_weight": line_weight,
            "stroke_color": stroke_color
        })
    return lines

def cluster_lines(items, max_dist):
    if not items:
        return []
    
    grid = {}
    clusters = []
    cluster_to_cells = {}
    
    def get_grid_cells(item):
        if item.get("shape_type") == "rect":
            x, y, w, h = item["x"], item["y"], item["width"], item["height"]
            pts = [(x, y), (x+w, y), (x+w, y+h), (x, y+h)]
        else:
            pts = item.get("points", [item["start"], item["end"]])
        
        cells = set()
        for p in pts:
            cx = int(math.floor(p[0] / max_dist))
            cy = int(math.floor(p[1] / max_dist))
            cells.add((cx, cy))
        return pts, cells

    def are_points_close(pts1, pts2, d_limit):
        for p1 in pts1:
            for p2 in pts2:
                dx = p1[0] - p2[0]
                if abs(dx) > d_limit:
                    continue
                dy = p1[1] - p2[1]
                if abs(dy) > d_limit:
                    continue
                if (dx*dx + dy*dy) <= d_limit*d_limit:
                    return True
        return False

    for item in items:
        pts, cells = get_grid_cells(item)
        
        candidate_cluster_indices = set()
        for cx, cy in cells:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor_cell = (cx + dx, cy + dy)
                    if neighbor_cell in grid:
                        candidate_cluster_indices.update(grid[neighbor_cell])
        
        matched_clusters = []
        for idx in candidate_cluster_indices:
            if not clusters[idx]:
                continue
            is_close = False
            for c_item in clusters[idx]:
                if c_item.get("shape_type") == "rect":
                    cx, cy, cw, ch = c_item["x"], c_item["y"], c_item["width"], c_item["height"]
                    c_pts = [(cx, cy), (cx+cw, cy), (cx+cw, cy+ch), (cx, cy+ch)]
                else:
                    c_pts = c_item.get("points", [c_item["start"], c_item["end"]])
                
                if are_points_close(pts, c_pts, max_dist):
                    is_close = True
                    break
            if is_close:
                matched_clusters.append(idx)
        
        if not matched_clusters:
            new_idx = len(clusters)
            clusters.append([item])
            cluster_to_cells[new_idx] = set(cells)
            for cell in cells:
                grid.setdefault(cell, set()).add(new_idx)
        elif len(matched_clusters) == 1:
            matched_idx = matched_clusters[0]
            clusters[matched_idx].append(item)
            cluster_to_cells[matched_idx].update(cells)
            for cell in cells:
                grid.setdefault(cell, set()).add(matched_idx)
        else:
            target_idx = matched_clusters[0]
            clusters[target_idx].append(item)
            cluster_to_cells[target_idx].update(cells)
            for cell in cells:
                grid.setdefault(cell, set()).add(target_idx)
                
            merged_indices = sorted(matched_clusters[1:], reverse=True)
            for idx in merged_indices:
                clusters[target_idx].extend(clusters[idx])
                clusters[idx] = []
                
                cluster_to_cells[target_idx].update(cluster_to_cells[idx])
                for cell in cluster_to_cells[idx]:
                    if cell in grid:
                        grid[cell].discard(idx)
                        grid[cell].add(target_idx)
                del cluster_to_cells[idx]
                
    return [c for c in clusters if c]


def match_pattern(cluster, signature, scan_cfg):
    sig_segs = signature["segments"]
    if len(cluster) < len(sig_segs):
        return None
    
    pos_tol = scan_cfg["position_tolerance"]
    len_tol = scan_cfg["length_tolerance"]
    weight_tol = scan_cfg["line_weight_tolerance"]
    color_tol = scan_cfg["color_tolerance"]

    for anchor_item in cluster:
        if anchor_item["shape_type"] != sig_segs[0].get("shape_type", "line"): continue
        if abs(anchor_item["length"] - sig_segs[0]["length"]) > len_tol: continue
        if abs(anchor_item["line_weight"] - sig_segs[0]["line_weight"]) > weight_tol: continue
        if not matching_lines.colors_match(anchor_item["stroke_color"], sig_segs[0]["stroke_color"], color_tol): continue
            
        for flip in [False, True]:
            # Translation anchor
            anchor_start = anchor_item["start"] if not flip else anchor_item["end"]
            tx, ty = anchor_start
            
            matched_items = [anchor_item]
            remaining_cluster = [l for l in cluster if l != anchor_item]
            all_matched = True
            
            for i in range(1, len(sig_segs)):
                sig_seg = sig_segs[i]
                shape_type = sig_seg.get("shape_type", "line")
                
                target_s = (sig_seg["start_rel"][0] + tx, sig_seg["start_rel"][1] + ty)
                target_e = (sig_seg["end_rel"][0] + tx, sig_seg["end_rel"][1] + ty)
                
                found_match = False
                for j, l in enumerate(remaining_cluster):
                    if l["shape_type"] != shape_type: continue
                    
                    # Quick bounding box/position check
                    p1 = l["start"]
                    p2 = l["end"]
                    p1_x, p1_y = p1[0], p1[1]
                    p2_x, p2_y = p2[0], p2[1]
                    ts_x, ts_y = target_s[0], target_s[1]
                    te_x, te_y = target_e[0], target_e[1]
                    
                    # Check X overlap
                    if min(p1_x, p2_x) - pos_tol > max(ts_x, te_x) or \
                       max(p1_x, p2_x) + pos_tol < min(ts_x, te_x):
                        continue
                        
                    # Check Y overlap
                    if min(p1_y, p2_y) - pos_tol > max(ts_y, te_y) or \
                       max(p1_y, p2_y) + pos_tol < min(ts_y, te_y):
                        continue
                        
                    if abs(l["length"] - sig_seg["length"]) > len_tol: continue
                    if abs(l["line_weight"] - sig_seg["line_weight"]) > weight_tol: continue
                    if not matching_lines.colors_match(l["stroke_color"], sig_seg["stroke_color"], color_tol): continue
                    
                    if shape_type == "line":
                        d_ss = matching_lines.dist(l["start"], target_s)
                        d_ee = matching_lines.dist(l["end"], target_e)
                        d_se = matching_lines.dist(l["start"], target_e)
                        d_es = matching_lines.dist(l["end"], target_s)
                        if (d_ss <= pos_tol and d_ee <= pos_tol) or (d_se <= pos_tol and d_es <= pos_tol):
                            matched_items.append(l)
                            remaining_cluster.pop(j)
                            found_match = True
                            break
                    elif shape_type == "rect":
                        d_s = matching_lines.dist(l["start"], target_s)
                        d_e = matching_lines.dist(l["end"], target_e)
                        if d_s <= pos_tol and d_e <= pos_tol:
                            matched_items.append(l)
                            remaining_cluster.pop(j)
                            found_match = True
                            break
                    elif shape_type == "arc":
                        pts_rel = sig_seg["points_rel"]
                        target_pts = [(p[0]+tx, p[1]+ty) for p in pts_rel]
                        l_pts = l["points"]
                        match_fwd = all(matching_lines.dist(l_pts[k], target_pts[k]) <= pos_tol for k in range(4))
                        match_rev = all(matching_lines.dist(l_pts[k], target_pts[3-k]) <= pos_tol for k in range(4))
                        if match_fwd or match_rev:
                            matched_items.append(l)
                            remaining_cluster.pop(j)
                            found_match = True
                            break
                    elif shape_type == "polygon":
                        pts_rel = sig_seg["points_rel"]
                        target_pts = [(p[0]+tx, p[1]+ty) for p in pts_rel]
                        l_pts = l["points"]
                        n = min(len(l_pts), len(target_pts))
                        match_fwd = all(matching_lines.dist(l_pts[k], target_pts[k]) <= pos_tol for k in range(n))
                        match_rev = all(matching_lines.dist(l_pts[k], target_pts[n-1-k]) <= pos_tol for k in range(n))
                        if match_fwd or match_rev:
                            matched_items.append(l)
                            remaining_cluster.pop(j)
                            found_match = True
                            break
                
                if not found_match:
                    all_matched = False
                    break
            
            if all_matched:
                xs, ys = [], []
                for l in matched_items:
                    pts = l.get("points", [l["start"], l["end"]])
                    xs.extend([p[0] for p in pts])
                    ys.extend([p[1] for p in pts])
                        
                return {
                    "target": signature["target"],
                    "type": signature.get("type"),
                    "lines": matched_items,
                    "bbox": (min(xs), min(ys), max(xs), max(ys)),
                    "annot_width": signature.get("annot_width", max(xs) - min(xs)),
                    "annot_height": signature.get("annot_height", max(ys) - min(ys)),
                    "angle": signature["angle"]
                }
    return None


# --- Multiprocessing Workers ---

def scan_page_for_signatures_worker(args):
    """Phase 1: Find stamps on a specific page."""
    pdf_path, page_idx, targets = args
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    
    target_lookup = {subject_items.norm_text(t): t for t in targets}
    matches = []
    
    for annot in page.annots() or []:
        subject = annot.info.get("subject") or ""
        target_name = target_lookup.get(subject_items.norm_text(subject))
        if not target_name: continue

        annot_type = annot.type[1]
        if annot_type == "Stamp":
            styles = subject_items.get_stamp_styles(doc, annot)
            segments = [segment for style in styles for segment in style[4]]
            if segments:
                matches.append({"target": target_name, "segments": segments})
    
    doc.close()
    return matches


def detect_patterns_in_page_worker(args):
    """Phase 2: Find pattern matches on a specific page."""
    pdf_path, page_idx, signatures, scan_cfg = args
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    
    # Extract unique box dimensions from signatures for filtering rects
    box_dims = []
    for sig in signatures:
        if "width" in sig and "height" in sig:
            box_dims.append((sig["width"], sig["height"]))
            
    len_tol = scan_cfg.get("length_tolerance", 1.0)
    page_items = list(iter_page_items(page, box_dims=box_dims, len_tol=len_tol))
    
    filtered_items = []
    for item in page_items:
        matched_targets = set()
        for sig in signatures:
            for s in sig["segments"]:
                if item["shape_type"] != s.get("shape_type", "line"): continue
                
                if item["shape_type"] == "rect":
                    if abs(item["width"] - s["width"]) > scan_cfg["length_tolerance"]: continue
                    if abs(item["height"] - s["height"]) > scan_cfg["length_tolerance"]: continue
                else:
                    if abs(item["length"] - s["length"]) > scan_cfg["length_tolerance"]: continue
                    
                if abs(item["line_weight"] - s["line_weight"]) > scan_cfg["line_weight_tolerance"]: continue
                if not matching_lines.colors_match(item["stroke_color"], s["stroke_color"], scan_cfg["color_tolerance"]): continue
                matched_targets.add(sig["target"])
                break
            
        if matched_targets:
            item["matched_targets"] = list(matched_targets)
            filtered_items.append(item)
            
    # 2. Cluster and match
    patterns = []
    if filtered_items:
        clusters = cluster_lines(filtered_items, scan_cfg["dedupe_distance"])
        for cluster in clusters:
            for sig in signatures:
                match = match_pattern(cluster, sig, scan_cfg)
                if match:
                    match["page"] = page_idx + 1
                    patterns.append(match)
                    break
    
    num_clusters = len(clusters) if filtered_items else 0
    num_matching_items = len(filtered_items)
    
    doc.close()
    return page_idx, patterns, num_matching_items, num_clusters


def detect_patterns_parallel(pdf_path, cfg):
    print(subject_items.color_text("\nScanning for patterns (Parallel)...", subject_items.Ansi.BOLD))
    
    # Check if we are running in web/project context
    project_name = None
    normalized = os.path.normpath(pdf_path)
    parts = normalized.split(os.sep)
    for i, part in enumerate(parts):
        if part.lower() == "projects" and i + 1 < len(parts):
            project_name = parts[i + 1]
            break

    flat_stamp_matches = []
    loaded_from_saved_patterns = False
    
    if project_name:
        try:
            pattern_matches, patterns_path = subject_items.load_pdf_pattern_matches(pdf_path)
            if pattern_matches:
                print(f"Web Context: Loading pattern signatures from {patterns_path}")
                flat_stamp_matches.extend(pattern_matches)
                loaded_from_saved_patterns = True
        except Exception as e:
            print(f"Error loading saved patterns for pattern detection: {e}")

    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    doc.close()
    
    num_cores = min(os.cpu_count() or 4, num_pages)
    print(f"Using {num_cores} CPU cores for processing {num_pages} pages.")

    def run_phase_with_pool(args_list, worker, progress_cb=None, ordered=False):
        try:
            with multiprocessing.Pool(num_cores) as pool:
                iterator = pool.imap(worker, args_list) if ordered else pool.imap_unordered(worker, args_list)
                for index, result in enumerate(iterator, 1):
                    if progress_cb:
                        progress_cb(index, result)
        except (PermissionError, OSError) as e:
            print(f"Multiprocessing unavailable ({e}). Falling back to sequential scan.")
            for index, args in enumerate(args_list, 1):
                result = worker(args)
                if progress_cb:
                    progress_cb(index, result)

    if not loaded_from_saved_patterns:
        # --- Phase 1: Signatures ---
        print(subject_items.color_text("Phase 1: Extracting signatures...", subject_items.Ansi.CYAN))
        targets = cfg.get("targets", [])
        phase1_args = [(pdf_path, i, targets) for i in range(num_pages)]

        def phase1_progress(index, page_matches):
            flat_stamp_matches.extend(page_matches)
            if index % 5 == 0 or index == num_pages:
                print(f"  Processed {index}/{num_pages} pages for signatures...")

        run_phase_with_pool(phase1_args, scan_page_for_signatures_worker, progress_cb=phase1_progress, ordered=False)
    
    signatures = get_unique_signatures(flat_stamp_matches)
    
    if not signatures:
        print(subject_items.color_text("No stamp signatures found.", subject_items.Ansi.RED))
        return []

    print(f"Extracted {len(signatures)} unique signatures (including rotations).")

    # --- Phase 2: Patterns ---
    print(subject_items.color_text("Phase 2: Detecting patterns...", subject_items.Ansi.CYAN))
    scan_cfg = matching_lines.get_scan_config(cfg)
    phase2_args = [(pdf_path, i, signatures, scan_cfg) for i in range(num_pages)]
    
    detected_patterns = []
    results_by_page = defaultdict(int)
    
    def phase2_progress(index, result):
        page_idx, page_patterns, num_lines, num_clusters = result
        detected_patterns.extend(page_patterns)
        page_num = page_idx + 1
        results_by_page[page_num] = len(page_patterns)
        print(f"  Page {page_num}: {num_lines} matching lines, {num_clusters} clusters")

    run_phase_with_pool(phase2_args, detect_patterns_in_page_worker, progress_cb=phase2_progress, ordered=True)

    return detected_patterns


def main():
    cfg = subject_items.load_config()
    pdf_path = subject_items.select_pdf(cfg["paths"]["input_folder"])
    if not pdf_path:
        return
        
    patterns = detect_patterns_parallel(pdf_path, cfg)
    
    if patterns:
        print(subject_items.color_text(f"\nTotal patterns detected: {len(patterns)}", subject_items.Ansi.BOLD))
        detect_patterns_output.save_pattern_pdf(pdf_path, patterns, cfg)
    else:
        print(subject_items.color_text("\nNo patterns detected.", subject_items.Ansi.RED))


if __name__ == "__main__":
    main()
