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
    """
    Extract unique geometric signatures for each subject.
    A signature is a list of segments relative to the first segment's start point.
    """
    signatures = []
    seen_keys = set()

    for item in subject_matches:
        target = item["target"]
        segments = item.get("segments", [])
        if not segments:
            continue

        base_x, base_y = segments[0]["start"]
        
        annot_rect = item.get("rect")
        if annot_rect is not None:
            try:
                # Convert to plain floats (fitz.Rect may not survive multiprocessing pickle)
                annot_w = float(annot_rect[2]) - float(annot_rect[0])
                annot_h = float(annot_rect[3]) - float(annot_rect[1])
                annot_w = abs(annot_w)
                annot_h = abs(annot_h)
            except Exception:
                annot_w = annot_h = 0.0
        else:
            annot_w = annot_h = 0.0
        
        rel_segments = []
        for seg in segments:
            rel_segments.append({
                "start_rel": (seg["start"][0] - base_x, seg["start"][1] - base_y),
                "end_rel": (seg["end"][0] - base_x, seg["end"][1] - base_y),
                "length": seg["length"],
                "line_weight": seg.get("effective_line_weight", seg["line_weight"]),
                "stroke_color": seg["stroke_color"]
            })
        
        sig_key_parts = []
        for s in rel_segments:
            sig_key_parts.append((
                round(s["start_rel"][0], 2), round(s["start_rel"][1], 2),
                round(s["end_rel"][0], 2), round(s["end_rel"][1], 2),
                round(s["length"], 2),
                round(s["line_weight"], 2),
                tuple(round(c, 3) for c in (s["stroke_color"] or []))
            ))
        sig_key = (target, tuple(sorted(sig_key_parts)))

        if sig_key not in seen_keys:
            seen_keys.add(sig_key)
            for angle in [0, 90, 180, 270]:
                temp_segs = []
                for s in rel_segments:
                    temp_segs.append({
                        "start_rel": rotate_rel_point(s["start_rel"], angle),
                        "end_rel": rotate_rel_point(s["end_rel"], angle),
                        "length": s["length"],
                        "line_weight": s["line_weight"],
                        "stroke_color": s["stroke_color"]
                    })
                
                rx, ry = temp_segs[0]["start_rel"]
                for s in temp_segs:
                    s["start_rel"] = (s["start_rel"][0] - rx, s["start_rel"][1] - ry)
                    s["end_rel"] = (s["end_rel"][0] - rx, s["end_rel"][1] - ry)
                
                xs = [s["start_rel"][0] for s in temp_segs] + [s["end_rel"][0] for s in temp_segs]
                ys = [s["start_rel"][1] for s in temp_segs] + [s["end_rel"][1] for s in temp_segs]
                
                # Calculate the effective match weight (average of segment weights)
                seg_weights = [s["line_weight"] for s in temp_segs]
                match_weight = sum(seg_weights) / len(seg_weights) if seg_weights else 0.0

                signatures.append({
                    "target": target,
                    "segments": temp_segs,
                    "width": max(xs) - min(xs),
                    "height": max(ys) - min(ys),
                    "annot_width": annot_w if angle in [0, 180] else annot_h,
                    "annot_height": annot_h if angle in [0, 180] else annot_w,
                    "angle": angle,
                    "match_line_weight": match_weight,
                    "stroke_color": temp_segs[0]["stroke_color"]
                })
            
    return signatures


def cluster_lines(lines, max_dist):
    if not lines:
        return []
    
    clusters = []
    for line in lines:
        points = [line["start"], line["end"]]
        matched_clusters = []
        for i, cluster in enumerate(clusters):
            is_close = False
            for p1 in points:
                for c_line in cluster:
                    if matching_lines.dist(p1, c_line["start"]) <= max_dist or \
                       matching_lines.dist(p1, c_line["end"]) <= max_dist:
                        is_close = True
                        break
                if is_close: break
            if is_close:
                matched_clusters.append(i)
        
        if not matched_clusters:
            clusters.append([line])
        elif len(matched_clusters) == 1:
            clusters[matched_clusters[0]].append(line)
        else:
            new_cluster = [line]
            for i in sorted(matched_clusters, reverse=True):
                new_cluster.extend(clusters.pop(i))
            clusters.append(new_cluster)
    return clusters


def match_pattern(cluster, signature, scan_cfg):
    sig_segs = signature["segments"]
    if len(cluster) < len(sig_segs):
        return None
    
    pos_tol = scan_cfg["position_tolerance"]
    len_tol = scan_cfg["length_tolerance"]
    weight_tol = scan_cfg["line_weight_tolerance"]
    color_tol = scan_cfg["color_tolerance"]

    for anchor_line in cluster:
        if abs(anchor_line["length"] - sig_segs[0]["length"]) > len_tol: continue
        if abs(anchor_line["line_weight"] - sig_segs[0]["line_weight"]) > weight_tol: continue
        if not matching_lines.colors_match(anchor_line["stroke_color"], sig_segs[0]["stroke_color"], color_tol): continue
            
        for flip in [False, True]:
            anchor_start = anchor_line["start"] if not flip else anchor_line["end"]
            tx, ty = anchor_start
            
            matched_lines = [anchor_line]
            remaining_cluster = [l for l in cluster if l != anchor_line]
            all_matched = True
            
            for i in range(1, len(sig_segs)):
                target_s = (sig_segs[i]["start_rel"][0] + tx, sig_segs[i]["start_rel"][1] + ty)
                target_e = (sig_segs[i]["end_rel"][0] + tx, sig_segs[i]["end_rel"][1] + ty)
                
                found_match = False
                for j, l in enumerate(remaining_cluster):
                    if abs(l["length"] - sig_segs[i]["length"]) > len_tol: continue
                    if abs(l["line_weight"] - sig_segs[i]["line_weight"]) > weight_tol: continue
                    if not matching_lines.colors_match(l["stroke_color"], sig_segs[i]["stroke_color"], color_tol): continue
                    
                    d_ss = matching_lines.dist(l["start"], target_s)
                    d_ee = matching_lines.dist(l["end"], target_e)
                    d_se = matching_lines.dist(l["start"], target_e)
                    d_es = matching_lines.dist(l["end"], target_s)
                    
                    if (d_ss <= pos_tol and d_ee <= pos_tol) or (d_se <= pos_tol and d_es <= pos_tol):
                        matched_lines.append(l)
                        remaining_cluster.pop(j)
                        found_match = True
                        break
                
                if not found_match:
                    all_matched = False
                    break
            
            if all_matched:
                xs = [l["start"][0] for l in matched_lines] + [l["end"][0] for l in matched_lines]
                ys = [l["start"][1] for l in matched_lines] + [l["end"][1] for l in matched_lines]
                return {
                    "target": signature["target"],
                    "lines": matched_lines,
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
    
    # 1. Find all lines matching any segment of any signature
    # (Simplified find_matching_lines logic for single page)
    # We need a flat list of lengths and properties from signatures to match efficiently
    page_lines = list(matching_lines.iter_page_lines(page))
    
    # Create simple signatures for detect_matching_lines logic
    # signatures passed here are the relative ones
    temp_subject_matches = []
    for sig in signatures:
        # We only need enough info for line_matches_signature
        temp_subject_matches.append({
            "target": sig["target"],
            # Provide the pre-calculated match_line_weight
            "styles": [ (sig["match_line_weight"], sig["stroke_color"], 0, [s["length"] for s in sig["segments"]], []) ]
        })
    
    # Use matching_lines to find potential segments
    matching_sigs = matching_lines.make_signatures(temp_subject_matches)
    
    filtered_lines = []
    for line in page_lines:
        matched_targets = [
            sig["target"] for sig in matching_sigs 
            if matching_lines.line_matches_signature(line, sig, scan_cfg)
        ]
        if matched_targets:
            line["matched_targets"] = matched_targets
            filtered_lines.append(line)
            
    # 2. Cluster and match
    patterns = []
    if filtered_lines:
        clusters = cluster_lines(filtered_lines, scan_cfg["dedupe_distance"])
        for cluster in clusters:
            for sig in signatures:
                match = match_pattern(cluster, sig, scan_cfg)
                if match:
                    match["page"] = page_idx + 1
                    patterns.append(match)
                    break
    
    num_clusters = len(clusters) if filtered_lines else 0
    num_matching_lines = len(filtered_lines)
    
    doc.close()
    return page_idx, patterns, num_matching_lines, num_clusters


def detect_patterns_parallel(pdf_path, cfg):
    print(subject_items.color_text("\nScanning for patterns (Parallel)...", subject_items.Ansi.BOLD))
    
    doc = fitz.open(pdf_path)
    num_pages = len(doc)
    doc.close()
    
    num_cores = min(os.cpu_count() or 4, num_pages)
    print(f"Using {num_cores} CPU cores for processing {num_pages} pages.")

    # --- Phase 1: Signatures ---
    print(subject_items.color_text("Phase 1: Extracting signatures...", subject_items.Ansi.CYAN))
    targets = cfg.get("targets", [])
    phase1_args = [(pdf_path, i, targets) for i in range(num_pages)]
    
    flat_stamp_matches = []
    with multiprocessing.Pool(num_cores) as pool:
        # Use imap_unordered to show progress as pages finish
        for i, page_matches in enumerate(pool.imap_unordered(scan_page_for_signatures_worker, phase1_args)):
            flat_stamp_matches.extend(page_matches)
            if (i + 1) % 5 == 0 or (i + 1) == num_pages:
                print(f"  Processed {i + 1}/{num_pages} pages for signatures...")
    
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
    
    with multiprocessing.Pool(num_cores) as pool:
        for i, (page_idx, page_patterns, num_lines, num_clusters) in enumerate(pool.imap(detect_patterns_in_page_worker, phase2_args)):
            detected_patterns.extend(page_patterns)
            page_num = page_idx + 1
            results_by_page[page_num] = len(page_patterns)
            print(f"  Page {page_num}: {num_lines} matching lines, {num_clusters} clusters")

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
