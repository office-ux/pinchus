import os
import fitz
from collections import defaultdict
import detect_matching_lines as matching_lines
import detect_subject_items as subject_items


def get_unique_output_path(output_folder, pdf_path):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_folder, f"{base_name}_patterns_detected.pdf")
    if not os.path.exists(output_path):
        return output_path
    counter = 2
    while True:
        output_path = os.path.join(output_folder, f"{base_name}_patterns_detected_{counter}.pdf")
        if not os.path.exists(output_path):
            return output_path
        counter += 1


def _fit_fontsize(text, box_w, box_h):
    pad = 6
    max_w = max(box_w - pad * 2, 1)
    max_h = max(box_h - pad * 2, 1)
    lo, hi = 4.0, max_h
    for _ in range(16):
        mid = (lo + hi) / 2
        if fitz.get_text_length(text, fontname="helv", fontsize=mid) <= max_w:
            lo = mid
        else:
            hi = mid
    return max(4.0, lo)



def _add_pattern_tag(page, tag_rect, num_text, color, label_color):
    """Create a custom-looking annotation and store it as a real Stamp subtype."""
    tag_w = tag_rect.width
    tag_h = tag_rect.height

    # Fixed font size: 50% of the smaller dimension
    fixed_fs = max(min(tag_w, tag_h) * 0.5, 6.0)

    annot = page.add_freetext_annot(
        tag_rect,
        num_text,
        fontsize=fixed_fs,
        fontname="helv",
        text_color=label_color,
        fill_color=(1.0, 1.0, 1.0),   # white background
        align=fitz.TEXT_ALIGN_CENTER,
    )

    # Subject = pattern name is set by the caller via set_info
    annot.set_border(width=2.0)
    annot.update()
    page.parent.xref_set_key(annot.xref, "Subtype", "/Stamp")
    annot = page.load_annot(annot.xref)
    return annot




def cluster_y_coordinates(patterns, tolerance=None):    # Rows height of stamps in points
    if tolerance is None:
        try:
            cfg = subject_items.load_config()
            tolerance = cfg.get("pattern_detection", {}).get("row_tolerance", 50.0)
        except Exception:
            tolerance = 50.0

    if not patterns:
        return []
    # Swap axes for -90 degree visual rotation:
    # We group by X (which corresponds to visual Y/rows)
    # and sort by Y (which corresponds to visual X/columns).
    
    # Sort patterns primarily by X center descending, secondarily by Y center ascending
    sorted_by_x = sorted(patterns, key=lambda p: (
        -((p["bbox"][0] + p["bbox"][2]) / 2),
        (p["bbox"][1] + p["bbox"][3]) / 2
    ))
    
    # Group them into vertical bands (non-drifting: compare to first element of the band)
    bands = []
    current_band = []
    
    for p in sorted_by_x:
        cx = (p["bbox"][0] + p["bbox"][2]) / 2
        if not current_band:
            current_band.append(p)
        else:
            first_cx = (current_band[0]["bbox"][0] + current_band[0]["bbox"][2]) / 2
            if abs(cx - first_cx) <= tolerance:
                current_band.append(p)
            else:
                bands.append(current_band)
                current_band = [p]
    if current_band:
        bands.append(current_band)
        
    # Now, for each band, sort top-to-bottom (by Y coordinate)
    sorted_patterns = []
    for band in bands:
        sorted_band = sorted(band, key=lambda p: (p["bbox"][1] + p["bbox"][3]) / 2)
        sorted_patterns.extend(sorted_band)
        
    return sorted_patterns


def save_pattern_pdf(pdf_path, detected_patterns, cfg):
    output_folder = cfg["paths"]["output_folder"]
    os.makedirs(output_folder, exist_ok=True)
    output_path = get_unique_output_path(output_folder, pdf_path)

    doc = fitz.open(pdf_path)
    unique_targets = sorted(list(set(p["target"] for p in detected_patterns)))
    color_map = matching_lines.get_target_color_map(unique_targets)

    pd_cfg = cfg.get("pattern_detection", {})
    tag_scale   = pd_cfg.get("tag_scale", 1.0)
    row_tolerance = pd_cfg.get("row_tolerance", 50.0)
    label_color = tuple(pd_cfg.get("tag_text_color", [1.0, 0.0, 0.0]))

    # Group patterns by target/grill type
    patterns_by_target = defaultdict(list)
    for p in detected_patterns:
        patterns_by_target[p["target"]].append(p)

    numbered_patterns = []

    # Assign sequential numbers per target, sorted page-by-page, row-by-row, left-to-right
    for target, target_list in patterns_by_target.items():
        by_page = defaultdict(list)
        for p in target_list:
            by_page[p["page"]].append(p)

        seq_num = 0
        for page_num in sorted(by_page.keys()):
            page_patterns = by_page[page_num]
            sorted_page_patterns = cluster_y_coordinates(page_patterns, tolerance=row_tolerance)
            for p in sorted_page_patterns:
                seq_num += 1
                numbered_patterns.append((seq_num, p))

    # Re-group by page for drawing
    patterns_by_page = defaultdict(list)
    for seq_num, pattern in numbered_patterns:
        patterns_by_page[pattern["page"]].append((seq_num, pattern))

    for page_num in sorted(patterns_by_page.keys()):
        page = doc[page_num - 1]

        # Draw all detection lines in one Shape commit per page
        shape = page.new_shape()
        for i, pattern in patterns_by_page[page_num]:
            color = color_map[pattern["target"]]
            for line in pattern["lines"]:
                shape.draw_line(line["start"], line["end"])
            shape.finish(color=color, width=4.0, stroke_opacity=0.8)
        shape.commit(overlay=True)

        # Add one Stamp annotation per pattern
        for i, pattern in patterns_by_page[page_num]:
            color  = color_map[pattern["target"]]
            bbox   = pattern["bbox"]
            cx     = (bbox[0] + bbox[2]) / 2
            cy     = (bbox[1] + bbox[3]) / 2

            # Use the actual bounding box of the matched lines, scaled by tag_scale
            # This is always correct for the detected pattern size regardless of source stamp
            raw_w  = bbox[2] - bbox[0]
            raw_h  = bbox[3] - bbox[1]
            tag_w  = max(raw_w * tag_scale, 20.0)
            tag_h  = max(raw_h * tag_scale, 20.0)

            tag_rect = fitz.Rect(cx - tag_w/2, cy - tag_h/2, cx + tag_w/2, cy + tag_h/2)

            annot = _add_pattern_tag(page, tag_rect, str(i), color, label_color)
            annot.set_info(subject=pattern["target"], title=f"Pattern #{i}")
            annot.update()
            print(f"  Pattern #{i}: {pattern['target']} (angle {pattern['angle']}) Page {page_num}")



    page_counts = defaultdict(int)
    for p in detected_patterns:
        page_counts[p["page"]] += 1

    print(subject_items.color_text("\nSummary by Page:", subject_items.Ansi.BOLD))
    for page_num in sorted(page_counts.keys()):
        print(f"  Page {page_num}: {page_counts[page_num]} patterns")

    doc.save(output_path)
    doc.close()
    print(subject_items.color_text(f"\nSaved pattern detection PDF to: {output_path}", subject_items.Ansi.GREEN))
    try:
        os.startfile(output_path)
    except Exception:
        pass
