

import fitz  # PyMuPDF
import os
import math
import json
import time
from collections import defaultdict

def load_config(config_path="config.json"):
    """Loads the central configuration file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")
        return None

def select_pdf_from_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return None
        
    pdfs = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not pdfs:
        print(f"No PDF files found in {folder_path}")
        return None
        
    print(f"PDF files found in {folder_path}:")
    for i, pdf in enumerate(pdfs, 1):
        print(f"{i}. {pdf}")
        
    while True:
        choice = input(f"Enter the number of the file to scan (1-{len(pdfs)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(pdfs):
                return os.path.join(folder_path, pdfs[idx])
        print("Invalid selection. Please try again.")

def dist(p1, p2):
    return math.hypot(p2[0]-p1[0], p2[1]-p1[1])

def normalize_seg(s):
    """Sorts endpoints of a segment to make it direction-agnostic."""
    p1, p2 = s
    if p1[0] < p2[0] or (p1[0] == p2[0] and p1[1] < p2[1]):
        return (p1, p2)
    return (p2, p1)

def format_pt_values(values):
    rounded = sorted(set(round(v, 2) for v in values))
    return ", ".join(f"{v:.2f}pt" for v in rounded)

def get_page_segments(page):
    """Extracts all line segments from a page's vector drawings with width and color."""
    drawings = page.get_drawings()
    segments = []
    for d in drawings:
        width = d.get("width")
        if width is None: width = 1.0
        color = d.get("color")
        if color is None: color = (0, 0, 0)
        for item in d["items"]:
            if item[0] == "l":
                segments.append({
                    "geom": normalize_seg((item[1], item[2])),
                    "width": width,
                    "color": color
                })
            elif item[0] == "re":
                r = item[1]
                rect_segs = [
                    ((r.x0, r.y0), (r.x1, r.y0)),
                    ((r.x1, r.y0), (r.x1, r.y1)),
                    ((r.x1, r.y1), (r.x0, r.y1)),
                    ((r.x0, r.y1), (r.x0, r.y0))
                ]
                for s in rect_segs:
                    segments.append({
                        "geom": normalize_seg(s),
                        "width": width,
                        "color": color
                    })
    return segments

def extract_templates(doc):
    """Finds 'grill' annotations and extracts the vector lines within them as templates."""
    templates = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        drawings = page.get_drawings()
        
        for annot in page.annots():
            subject = (annot.info.get("subject") or "").lower()
            if "grill" in subject:
                # Expand rect slightly to ensure we catch lines on the boundary
                rect = annot.rect + (-2, -2, 2, 2) 
                template_segs = []
                for d in drawings:
                    d_rect = fitz.Rect(d["rect"])
                    if not d_rect.intersects(rect):
                        continue
                    width = d.get("width")
                    if width is None: width = 1.0
                    color = d.get("color")
                    if color is None: color = (0, 0, 0)
                    for item in d["items"]:
                        if item[0] == "l":
                            p1, p2 = item[1], item[2]
                            if p1 in rect and p2 in rect:
                                template_segs.append({
                                    "geom": normalize_seg((p1, p2)),
                                    "width": width,
                                    "color": color
                                })
                        elif item[0] == "re":
                            r = item[1]
                            if fitz.Rect(r).intersects(rect):
                                rect_segs = [
                                    ((r.x0, r.y0), (r.x1, r.y0)),
                                    ((r.x1, r.y0), (r.x1, r.y1)),
                                    ((r.x1, r.y1), (r.x0, r.y1)),
                                    ((r.x0, r.y1), (r.x0, r.y0))
                                ]
                                for s in rect_segs:
                                    if s[0] in rect and s[1] in rect:
                                        template_segs.append({
                                            "geom": normalize_seg(s),
                                            "width": width,
                                            "color": color
                                        })
                
                if template_segs:
                    # Sort by length descending
                    template_segs.sort(key=lambda s: dist(s["geom"][0], s["geom"][1]), reverse=True)
                    
                    min_x = min(min(s["geom"][0][0], s["geom"][1][0]) for s in template_segs)
                    min_y = min(min(s["geom"][0][1], s["geom"][1][1]) for s in template_segs)
                    
                    norm_segs = []
                    for s in template_segs:
                        p1 = (s["geom"][0][0] - min_x, s["geom"][0][1] - min_y)
                        p2 = (s["geom"][1][0] - min_x, s["geom"][1][1] - min_y)
                        norm_segs.append({
                            "geom": normalize_seg((p1, p2)),
                            "width": s["width"],
                            "color": s["color"]
                        })
                    
                    templates.append({
                        "page": page_num,
                        "segments": norm_segs,
                        "bbox_width": max(max(s["geom"][0][0], s["geom"][1][0]) for s in template_segs) - min_x,
                        "bbox_height": max(max(s["geom"][0][1], s["geom"][1][1]) for s in template_segs) - min_y
                    })
                    unique_widths = sorted(list(set(s["width"] for s in template_segs)))
                    unique_lengths = [dist(s["geom"][0], s["geom"][1]) for s in template_segs]
                    print(f"Extracted template from Page {page_num+1} with {len(template_segs)} segments.")
                    print(f"  Grille border/outline lengths: {format_pt_values(unique_lengths)}")
                    print(f"  Longest grille border/outline: {dist(template_segs[0]['geom'][0], template_segs[0]['geom'][1]):.2f} pt")
                    print(f"  PDF stroke thickness values: {', '.join(f'{w:.2f}pt' for w in unique_widths)}")
    
    return templates

def find_matches(page_segs, template, grill_cfg):
    """Searches for occurrences of the template using an exhaustive geometric match with width/color filtering."""
    if not template["segments"]:
        return []
    
    tolerance = grill_cfg["tolerance"]
    threshold = grill_cfg["threshold"]
    grid_size = grill_cfg["grid_size"]
    
    start_time = time.time()
    matches = []
    t_segs = template["segments"]
    t_count = len(t_segs)
    
    # --- SPATIAL OPTIMIZATION ---
    spatial_grid = defaultdict(list)
    for s in page_segs:
        p1, p2 = s["geom"]
        spatial_grid[(round(p1[0]/grid_size), round(p1[1]/grid_size))].append(s)
        spatial_grid[(round(p2[0]/grid_size), round(p2[1]/grid_size))].append(s)

    # --- EXHAUSTIVE SEARCH ---
    all_page_segments = page_segs
    print(f"  Checking {len(all_page_segments)} potential starting segments...")
    
    t0 = t_segs[0]
    t_a1_len = dist(t0["geom"][0], t0["geom"][1])
    total_segs = len(all_page_segments)
    for idx, ps in enumerate(all_page_segments):
        if idx % 50 == 0 or idx == total_segs - 1:
            elapsed = time.time() - start_time
            print(f"\r    Progress: {idx + 1}/{total_segs} | Time: {elapsed:.1f}s", end="", flush=True)

        # 1. Geometry Filter (Length)
        ps_len = dist(ps["geom"][0], ps["geom"][1])
        if abs(ps_len - t_a1_len) > (tolerance + 0.5):
            continue

        # 2. Line Weight Filter
        if abs(ps["width"] - t0["width"]) > 0.1: # Small tolerance for floating point line weights
            continue

        # 3. Color Filter (Optional but recommended)
        if ps["color"] != t0["color"]:
            continue

        for c_p1, c_p2 in [ps["geom"], (ps["geom"][1], ps["geom"][0])]:
            dx = c_p1[0] - t0["geom"][0][0]
            dy = c_p1[1] - t0["geom"][0][1]
            
            matched_count = 1
            for i in range(1, t_count):
                target_t = t_segs[i]
                target_p1 = (target_t["geom"][0][0] + dx, target_t["geom"][0][1] + dy)
                target_p2 = (target_t["geom"][1][0] + dx, target_t["geom"][1][1] + dy)
                
                found_seg = False
                gx, gy = round(target_p1[0]/grid_size), round(target_p1[1]/grid_size)
                for ox in [-1, 0, 1]:
                    for oy in [-1, 0, 1]:
                        for grid_s in spatial_grid.get((gx + ox, gy + oy), []):
                            # Check geometry, width, and color
                            if abs(grid_s["width"] - target_t["width"]) > 0.1:
                                continue
                            if grid_s["color"] != target_t["color"]:
                                continue
                                
                            gs_p1, gs_p2 = grid_s["geom"]
                            if ((dist(gs_p1, target_p1) < tolerance and dist(gs_p2, target_p2) < tolerance) or
                                (dist(gs_p2, target_p1) < tolerance and dist(gs_p1, target_p2) < tolerance)):
                                found_seg = True
                                break
                        if found_seg: break
                    if found_seg: break
                
                if found_seg:
                    matched_count += 1
            
            if matched_count / t_count >= threshold:
                cx = dx + template["bbox_width"] / 2
                cy = dy + template["bbox_height"] / 2
                if not any(dist((cx, cy), m) < 15 for m in matches):
                    matches.append((cx, cy))
                break
                
    print(f"Match phase took {time.time() - start_time:.2f} seconds.")
    return matches

def detect_grills():
    cfg = load_config()
    if not cfg:
        return
        
    folder_path = cfg["paths"]["input_folder"]
    pdf_path = select_pdf_from_folder(folder_path)
    if not pdf_path:
        return

    doc = fitz.open(pdf_path)
    templates = extract_templates(doc)
    
    if not templates:
        print("No 'grill' stamps found to use as templates.")
        return

    grill_cfg = cfg["grill_detection"]
    total_matches = 0
    tag_counter = 1
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"Scanning Page {page_num+1}/{len(doc)}...")
        page_segs = get_page_segments(page)
        
        if not page_segs:
            continue

        page_matches = []
        for template in templates:
            # Apply every template found to every page
            matches = find_matches(page_segs, template, grill_cfg)
            page_matches.extend(matches)
        
        unique_matches = []
        for m in page_matches:
            # Prevent double-tagging the same location
            if not any(dist(m, um) < 10 for um in unique_matches):
                unique_matches.append(m)
        
        for cx, cy in unique_matches:
            label = str(tag_counter)
            fs = grill_cfg["tag_font_size"]
            tw = fitz.get_text_length(label, fontsize=fs)
            text_rect = fitz.Rect(cx - tw/2 - 2, cy - fs/2 - 2, cx + tw/2 + 2, cy + fs/2 + 2)
            
            annot = page.add_freetext_annot(
                text_rect, label,
                fontsize=fs,
                text_color=tuple(grill_cfg["tag_text_color"]),
                fill_color=None  # Transparent background
            )
            annot.set_info(subject="Grill Tag")
            annot.update()
            
            tag_counter += 1
            total_matches += 1
            
        if unique_matches:
            print(f"Page {page_num+1}: Found {len(unique_matches)} matching grills.")

    if total_matches > 0:
        out_dir = cfg["paths"]["output_folder"]
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        base_name = os.path.basename(pdf_path).replace(".pdf", "_grills_detected.pdf")
        out_path = os.path.join(out_dir, base_name)
        
        doc.save(out_path)
        print(f"Detection complete! Found {total_matches} grills.")
        print(f"Saved to: {out_path}")
        
        try:
            os.startfile(out_path)
        except:
            pass
    else:
        print("No matching grills found.")

if __name__ == "__main__":
    detect_grills()
