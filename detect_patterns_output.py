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


def _add_pattern_tag(page, tag_rect, num_text, color, label_color, pdf_path, pattern_name):
    # Add a text annotation with the number inside the rect
    # Fixed font size: 50% of the smaller dimension
    fixed_fs = max(min(tag_rect.width, tag_rect.height) * 0.5, 6.0)

    bg_color = (1.0, 1.0, 1.0) if color is not None else None
    
    # If custom shape is applied, color might be 'transparent_bg'
    if color == 'transparent_bg':
        bg_color = None
        
    annot = page.add_freetext_annot(
        tag_rect,
        num_text,
        fontsize=fixed_fs,
        fontname="helv",
        text_color=label_color,
        fill_color=bg_color,
        align=fitz.TEXT_ALIGN_CENTER,
    )

    if color != 'transparent_bg':
        annot.set_border(width=2.0)
    else:
        annot.set_border(width=0.0)

    annot.update()

    import urllib.parse
    import uuid
    
    stamp_id = str(uuid.uuid4())
    encoded_pdf = urllib.parse.quote(pdf_path.replace("\\", "/"))
    base_url = "https://tabsoftwear.salcerandco.com/"
    link = {
        "kind": fitz.LINK_URI,  # external URI link
        "from": tag_rect,
        "uri": f"{base_url}?pdf={encoded_pdf}#stamp-{stamp_id}"
    }
    page.insert_link(link)
    
    link_xref = None
    annots_val = page.parent.xref_get_key(page.xref, "Annots")
    if annots_val[0] == "array":
        parts = annots_val[1].replace("[", "").replace("]", "").split()
        if len(parts) >= 3:
            link_xref = int(parts[-3])

    return annot, link_xref, stamp_id


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


def get_target_types_map(pdf_path):
    import json
    # Find project name
    project_name = None
    normalized = os.path.normpath(pdf_path)
    parts = normalized.split(os.sep)
    for i, part in enumerate(parts):
        if part.lower() == "projects" and i + 1 < len(parts):
            project_name = parts[i + 1]
            break
            
    types_map = {}
    if project_name:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(base_dir).lower() in ("working_testing_scripts", "web_viewer"):
            base_dir = os.path.dirname(base_dir)
            
        # First, try to load from the pdf patterns json file if it exists
        pdf_name = os.path.basename(pdf_path)
        for path_option in [
            os.path.join(base_dir, "Projects", project_name, "patterns", f"{pdf_name}_patterns.json"),
            os.path.join("Projects", project_name, "patterns", f"{pdf_name}_patterns.json")
        ]:
            if os.path.exists(path_option):
                try:
                    with open(path_option, "r", encoding="utf-8") as f:
                        patterns = json.load(f)
                        for pattern in patterns:
                            if pattern.get("name") and pattern.get("type"):
                                types_map[pattern["name"]] = pattern["type"]
                    break
                except Exception:
                    pass

        # Check both potential paths for annotations.json
        for path_option in [
            os.path.join(base_dir, "Projects", project_name, "annotations.json"),
            os.path.join("Projects", project_name, "annotations.json")
        ]:
            if os.path.exists(path_option):
                try:
                    with open(path_option, "r", encoding="utf-8") as f:
                        annotations = json.load(f)
                        for ann in annotations:
                            if ann.get("name") and ann.get("type"):
                                types_map[ann["name"]] = ann["type"]
                    break
                except Exception:
                    pass
    return types_map


def save_pattern_pdf(pdf_path, detected_patterns, cfg, output_path=None, overwrite_input=False):
    if overwrite_input:
        output_path = pdf_path
    elif output_path is None:
        output_folder = cfg["paths"]["output_folder"]
        os.makedirs(output_folder, exist_ok=True)
        output_path = get_unique_output_path(output_folder, pdf_path)

    doc = fitz.open(pdf_path)
    
    # Create the OCG layer named Vector PDF Inspector
    inspector_ocg = doc.add_ocg("Vector PDF Inspector", on=True)
    hyperlinks_ocg = doc.add_ocg("TAB hyperlinks", on=True)

    # Load global stamp config
    global_config = {}
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "global_stamp_config.json")
    if not os.path.exists(config_path):
        # try relative to web_viewer
        config_path = os.path.join(os.path.dirname(__file__), "global_stamp_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                global_config = json.load(f)
        except Exception as e:
            print("Error loading global stamp config:", e)

    sample_doc = None
    sample_stamps_cache = {}
    if global_config.get("rules"):
        sample_path = os.path.join(os.path.dirname(config_path), "web_viewer", "data", "global_stamps", "sample_stamps.pdf")
        if os.path.exists(sample_path):
            try:
                sample_doc = fitz.open(sample_path)
                # Cache all stamps on page 0
                for annot in sample_doc[0].annots() or []:
                    if annot.type[1] == "Stamp":
                        name = annot.info.get("title") or annot.info.get("subject") or annot.info.get("name")
                        if name:
                            sample_stamps_cache[name] = annot.rect
            except Exception as e:
                print("Error loading sample_stamps.pdf:", e)

    def evaluate_rules(pattern_data, rules, rule_type):
        for rule in rules:
            if rule.get("type") != rule_type:
                continue
            field = rule.get("field", "")
            op = rule.get("operator", "==")
            val = rule.get("value", "")
            
            # Check pattern attributes
            actual_val = ""
            if field.lower() in ("type", "target", "name", "pattern"):
                actual_val = pattern_data.get("type") or pattern_data.get("target") or ""
            elif field.lower() in ("system", "air outlet", "air_outlet"):
                # Handle special aliases
                tt = pattern_data.get("type") or pattern_data.get("target") or ""
                actual_val = "air outlet" if tt in ("grill", "air outlet", "vent") else "system"
                
            actual_val = str(actual_val).lower()
            val = str(val).lower()
            
            is_match = False
            if op == "==" and actual_val == val:
                is_match = True
            elif op == "!=" and actual_val != val:
                is_match = True
                
            if is_match:
                return rule.get("result")
        return None



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

    # Load target types to determine if a target is an air outlet or system
    target_types = get_target_types_map(pdf_path)

    xref_overrides = []

    for page_num in sorted(patterns_by_page.keys()):
        page = doc[page_num - 1]

        # Skip drawing individual lines, only create the stamp annotations below

        # Add one Stamp annotation per pattern
        for i, pattern in patterns_by_page[page_num]:
            color  = color_map[pattern["target"]]
            bbox   = pattern["bbox"]
            cx     = (bbox[0] + bbox[2]) / 2
            cy     = (bbox[1] + bbox[3]) / 2

            # Use the actual bounding box of the matched lines, scaled by tag_scale
            raw_w  = bbox[2] - bbox[0]
            raw_h  = bbox[3] - bbox[1]
            tag_w  = max(raw_w * tag_scale, 20.0)
            tag_h  = max(raw_h * tag_scale, 20.0)

            tag_rect = fitz.Rect(cx - tag_w/2, cy - tag_h/2, cx + tag_w/2, cy + tag_h/2)

            # Determine subject based on parent type
            target_name = pattern["target"]
            target_type = pattern.get("type") or target_types.get(target_name, "")
            if not target_type:
                # Fallback: check target name contents
                if "grill" in target_name.lower() or "outlet" in target_name.lower():
                    target_type = "grill"
                else:
                    target_type = "aac_unit"
                    
            if target_type in ("grill", "air outlet", "air_outlet", "vent"):
                stamp_subject = "air outlet"
            else:
                stamp_subject = "system"
                
            pattern_data_for_rules = {"target": target_name, "type": target_type}
            
            # Evaluate Color Rule
            custom_color_hex = evaluate_rules(pattern_data_for_rules, global_config.get("rules", []), "color")
            if custom_color_hex:
                # convert hex to rgb
                custom_color_hex = custom_color_hex.lstrip('#')
                if len(custom_color_hex) == 6:
                    r, g, b = tuple(int(custom_color_hex[i:i+2], 16) / 255.0 for i in (0, 2, 4))
                    label_color = (r, g, b)
                    
            # Evaluate Shape Rule
            custom_shape_name = evaluate_rules(pattern_data_for_rules, global_config.get("rules", []), "shape")
            if custom_shape_name and sample_doc and custom_shape_name in sample_stamps_cache:
                src_rect = sample_stamps_cache[custom_shape_name]
                try:
                    page.show_pdf_page(tag_rect, sample_doc, 0, clip=src_rect)
                    # We make the freetext annot background transparent since we rendered the shape
                    color = 'transparent_bg'
                except Exception as e:
                    print("Error drawing custom shape:", e)
                    
            annot, link_xref, stamp_uuid = _add_pattern_tag(page, tag_rect, str(i), color, label_color, pdf_path, target_name)
            annot.set_info(subject=stamp_subject, title="")
            annot.update()
            
            # Save overrides for second pass
            xref_overrides.append((annot.xref, target_name, stamp_uuid, inspector_ocg, i))
            
            if link_xref:
                doc.xref_set_key(link_xref, "OC", f"{hyperlinks_ocg} 0 R")
            print(f"  Pattern #{i}: {pattern['target']} (angle {pattern['angle']}) Page {page_num}")

    page_counts = defaultdict(int)
    for p in detected_patterns:
        page_counts[p["page"]] += 1

    print(subject_items.color_text("\nSummary by Page:", subject_items.Ansi.BOLD))
    for page_num in sorted(page_counts.keys()):
        print(f"  Page {page_num}: {page_counts[page_num]} patterns")

    if overwrite_input:
        doc.saveIncr()
        doc.close()
    else:
        doc.save(output_path)
        doc.close()

    if sample_doc:
        sample_doc.close()

    # === SECOND PASS ===
    # PyMuPDF aggressively overwrites non-unique /NM fields and regenerates annotation keys 
    # during doc.save() if the annot object was loaded in memory. 
    # To forcefully write our desired metadata, we perform a second pass entirely via xrefs.
    override_path = output_path if not overwrite_input else pdf_path
    doc2 = fitz.open(override_path)
    for xref, t_name, s_uuid, ocg_id, seq_num in xref_overrides:
        doc2.xref_set_key(xref, "Subtype", "/Stamp")
        doc2.xref_set_key(xref, "NM", f"({t_name}_{seq_num})")
        doc2.xref_set_key(xref, "Name", f"/{s_uuid}")
        doc2.xref_set_key(xref, "StampID", f"({s_uuid})")
        doc2.xref_set_key(xref, "OC", f"{ocg_id} 0 R")
    
    tmp_path = override_path + ".tmp"
    doc2.save(tmp_path)
    doc2.close()
    
    import shutil
    shutil.move(tmp_path, override_path)
    # ===================

    print(subject_items.color_text(f"\nSaved pattern detection PDF to: {override_path}", subject_items.Ansi.GREEN))
    if not overwrite_input:
        try:
            os.startfile(override_path)
        except Exception:
            pass
    return override_path
