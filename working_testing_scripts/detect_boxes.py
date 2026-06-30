import math
import os
import fitz
import detect_subject_items as subject_items
import detect_patterns
import detect_matching_lines as matching_lines

def iter_page_items_exploded(page):
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
                    "length": matching_lines.dist((start[0], start[1]), (end[0], end[1])),
                    "line_weight": line_weight,
                    "stroke_color": stroke_color,
                }
            elif item[0] == "re":
                rect = item[1]
                points = [
                    ((rect.x0, rect.y0), (rect.x1, rect.y0)),
                    ((rect.x1, rect.y0), (rect.x1, rect.y1)),
                    ((rect.x1, rect.y1), (rect.x0, rect.y1)),
                    ((rect.x0, rect.y1), (rect.x0, rect.y0)),
                ]
                for rect_index, (start, end) in enumerate(points, 1):
                    yield {
                        "source": f"{source_lbl}, rect side {rect_index}",
                        "shape_type": "line",
                        "start": start,
                        "end": end,
                        "length": matching_lines.dist(start, end),
                        "line_weight": line_weight,
                        "stroke_color": stroke_color,
                    }
            elif item[0] == "qu":
                points = [
                    ((item[1][0].x, item[1][0].y), (item[1][1].x, item[1][1].y)),
                    ((item[1][1].x, item[1][1].y), (item[1][2].x, item[1][2].y)),
                    ((item[1][2].x, item[1][2].y), (item[1][3].x, item[1][3].y)),
                    ((item[1][3].x, item[1][3].y), (item[1][0].x, item[1][0].y)),
                ]
                for qu_index, (start, end) in enumerate(points, 1):
                    yield {
                        "source": f"{source_lbl}, qu side {qu_index}",
                        "shape_type": "line",
                        "start": start,
                        "end": end,
                        "length": matching_lines.dist(start, end),
                        "line_weight": line_weight,
                        "stroke_color": stroke_color,
                    }

def get_unique_signatures_exploded(subject_matches):
    signatures = []
    seen = set()
    for item in subject_matches:
        for style_weight, style_color, _, style_lengths, style_segments in item.get("styles", []):
            if not style_segments: continue
            
            # Compute bounding box of the stamp segments
            xs = []
            ys = []
            for s in style_segments:
                xs.extend([s["start"][0], s["end"][0]])
                ys.extend([s["start"][1], s["end"][1]])
            
            if not xs: continue
            
            w = abs(max(xs) - min(xs))
            h = abs(max(ys) - min(ys))
            
            # Determine dominant weight and color
            effective_weights = [s.get("effective_line_weight", s.get("line_weight", 1.0)) for s in style_segments]
            match_weight = sum(effective_weights) / len(effective_weights) if effective_weights else style_weight
            stroke_color = style_segments[0].get("stroke_color", (0,0,0))
            
            # Create a synthetic 4-line rect signature
            rect_segments = [
                {"start_rel": (0, 0), "end_rel": (w, 0), "length": w, "line_weight": match_weight, "stroke_color": stroke_color, "shape_type": "line"},
                {"start_rel": (w, 0), "end_rel": (w, h), "length": h, "line_weight": match_weight, "stroke_color": stroke_color, "shape_type": "line"},
                {"start_rel": (w, h), "end_rel": (0, h), "length": w, "line_weight": match_weight, "stroke_color": stroke_color, "shape_type": "line"},
                {"start_rel": (0, h), "end_rel": (0, 0), "length": h, "line_weight": match_weight, "stroke_color": stroke_color, "shape_type": "line"},
            ]
            
            sig_key = f"rect_{w:.1f}x{h:.1f}"
            
            for angle in [0, 90, 180, 270]:
                temp_segs = []
                for s in rect_segments:
                    new_s = s.copy()
                    temp_segs.append(new_s)
                
                theta = math.radians(angle)
                for s in temp_segs:
                    for k in ["start_rel", "end_rel"]:
                        x, y = s[k]
                        nx = x * math.cos(theta) - y * math.sin(theta)
                        ny = x * math.sin(theta) + y * math.cos(theta)
                        s[k] = (nx, ny)
                
                rotated_key = f"{sig_key}|rot_{angle}"
                if rotated_key not in seen:
                    seen.add(rotated_key)
                    
                    signatures.append({
                        "target": item["target"],
                        "angle": angle,
                        "line_weight": style_weight,
                        "match_line_weight": match_weight,
                        "stroke_color": style_color,
                        "segments": temp_segs
                    })
    return signatures

def test_detect_boxes():
    print(subject_items.color_text("\n--- TEST: BOX DETECTION OVERHAUL ---", subject_items.Ansi.BOLD))
    cfg = subject_items.load_config()
    pdf_path = subject_items.select_pdf(cfg["paths"]["input_folder"])
    if not pdf_path: return

    print(subject_items.color_text("\nScanning patterns...", subject_items.Ansi.CYAN))
    targets = cfg.get("targets", [])
    subject_matches, _ = subject_items.scan_pdf(pdf_path, targets)
    if not subject_matches: return

    signatures = get_unique_signatures_exploded(subject_matches)
    print(f"Extracted {len(signatures)} unique signatures (including rotations).")

    scan_cfg = cfg.get("pattern_detection", {})
    scan_cfg.setdefault("length_tolerance", 0.5)
    scan_cfg.setdefault("line_weight_tolerance", 0.2)
    scan_cfg.setdefault("color_tolerance", 0.05)
    scan_cfg.setdefault("dedupe_distance", 5.0)
    scan_cfg.setdefault("position_tolerance", 2.0)

    doc = fitz.open(pdf_path)
    all_patterns = []
    page_matches = []

    for page_idx in range(len(doc)):
        print(f"\nScanning Page {page_idx + 1}...")
        page = doc[page_idx]
        page_items = list(iter_page_items_exploded(page))
        
        filtered_items = []
        for item in page_items:
            matched_targets = set()
            for sig in signatures:
                for s in sig["segments"]:
                    if abs(item["length"] - s["length"]) > scan_cfg["length_tolerance"]: continue
                    if abs(item["line_weight"] - s.get("line_weight", 1.0)) > scan_cfg["line_weight_tolerance"]: continue
                    if not matching_lines.colors_match(item["stroke_color"], s.get("stroke_color", (0,0,0)), scan_cfg["color_tolerance"]): continue
                    matched_targets.add(sig["target"])
                    break
            if matched_targets:
                item["matched_targets"] = list(matched_targets)
                filtered_items.append(item)
                
        print(f"Found {len(filtered_items)} potentially matching individual lines on Page {page_idx + 1}.")
        
        clusters = detect_patterns.cluster_lines(filtered_items, scan_cfg["dedupe_distance"])
        
        patterns = []
        for cluster in clusters:
            for sig in signatures:
                match = detect_patterns.match_pattern(cluster, sig, scan_cfg)
                if match:
                    match["page"] = page_idx + 1
                    patterns.append(match)
                    all_patterns.append(match)
                    break
                
        print(f"Patterns Detected on Page {page_idx + 1}: {len(patterns)}")
        
        box_lines = []
        for match in patterns:
            min_x, min_y, max_x, max_y = match["bbox"]
            box_lines.append({
                "source": "detected box",
                "shape_type": "rect",
                "x": min_x,
                "y": min_y,
                "width": max_x - min_x,
                "height": max_y - min_y,
                "matched_targets": [match["target"]]
            })
            
        page_matches.append({"page": page_idx + 1, "lines": box_lines})
        
    matching_lines.save_layered_matching_pdf(pdf_path, page_matches, cfg)
    
    print(f"\nTotal Patterns Detected across all pages: {len(all_patterns)}")
    for i, p in enumerate(all_patterns):
        print(f" - {p['target']} (angle {p['angle']}) at X:{p['bbox'][0]:.1f}, Y:{p['bbox'][1]:.1f}")
        
    print("\nTest completed successfully!")
    print("Boxes are preserved visually while still robustly matching exploded lines in the PDF data.")

if __name__ == "__main__":
    test_detect_boxes()
