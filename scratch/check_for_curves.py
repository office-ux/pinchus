import os
import sys
import json
import math
import multiprocessing

scripts_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Scripts'))
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

import fitz
import detect_subject_items as subject_items

def get_curve_signature(curve):
    """Calculates lengths between control points for rotation/translation invariant matching."""
    p0, p1, p2, p3 = curve
    d1 = math.hypot(p1[0]-p0[0], p1[1]-p0[1])
    d2 = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
    d3 = math.hypot(p3[0]-p2[0], p3[1]-p2[1])
    d4 = math.hypot(p3[0]-p0[0], p3[1]-p0[1])
    return (d1, d2, d3, d4)

def curves_match(c1, c2, tol):
    s1 = get_curve_signature(c1)
    s2 = get_curve_signature(c2)
    return all(abs(a - b) <= tol for a, b in zip(s1, s2))

def parse_curves_from_annot(doc, annot):
    """Parses a stamp annotation's appearance stream to extract bezier curves."""
    curves = []
    seen = set()
    pending = subject_items.get_stamp_appearance_xrefs(doc, annot.xref)
    
    while pending:
        xref = pending.pop(0)
        if xref in seen: continue
        seen.add(xref)
        stream = doc.xref_stream(xref)
        if stream:
            text = stream.decode('latin1', errors='ignore')
            import re
            tokens = re.findall(r'/[^\s<>\[\]()]+|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?|[A-Za-z*]+', text)
            stack = []
            ctm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
            current_point = None
            
            def pop_number(default=0.0):
                if not stack: return default
                try: return float(stack.pop())
                except ValueError: return default
                
            def concat_matrix(current, new):
                a1, b1, c1, d1, e1, f1 = current
                a2, b2, c2, d2, e2, f2 = new
                return (a1*a2+c1*b2, b1*a2+d1*b2, a1*c2+c1*d2, b1*c2+d1*d2, a1*e2+c1*f2+e1, b1*e2+d1*f2+f1)
                
            def transform_point(x, y):
                a, b, c, d, e, f = ctm
                return (a*x+c*y+e, b*x+d*y+f)
                
            for token in tokens:
                if token in {'q', 'Q', 'cm', 'm', 'l', 'c', 'v', 'y', 're', 'h', 'S', 's', 'B', 'b', 'n', 'f', 'F', 'B*', 'b*'}:
                    if token == 'cm':
                        f = pop_number()
                        e = pop_number()
                        d = pop_number()
                        c_val = pop_number()
                        b = pop_number()
                        a = pop_number()
                        ctm = concat_matrix(ctm, (a,b,c_val,d,e,f))
                        stack.clear()
                    elif token == 'm':
                        y = pop_number()
                        x = pop_number()
                        stack.clear()
                        current_point = transform_point(x, y)
                    elif token == 'l':
                        y = pop_number()
                        x = pop_number()
                        stack.clear()
                        current_point = transform_point(x, y)
                    elif token == 'c':
                        y3, x3 = pop_number(), pop_number()
                        y2, x2 = pop_number(), pop_number()
                        y1, x1 = pop_number(), pop_number()
                        stack.clear()
                        p1 = transform_point(x1, y1)
                        p2 = transform_point(x2, y2)
                        p3 = transform_point(x3, y3)
                        if current_point is not None:
                            curves.append((current_point, p1, p2, p3))
                        current_point = p3
                    elif token == 'v':
                        y3, x3 = pop_number(), pop_number()
                        y2, x2 = pop_number(), pop_number()
                        stack.clear()
                        p2 = transform_point(x2, y2)
                        p3 = transform_point(x3, y3)
                        if current_point is not None:
                            curves.append((current_point, current_point, p2, p3))
                        current_point = p3
                    elif token == 'y':
                        y3, x3 = pop_number(), pop_number()
                        y1, x1 = pop_number(), pop_number()
                        stack.clear()
                        p1 = transform_point(x1, y1)
                        p3 = transform_point(x3, y3)
                        if current_point is not None:
                            curves.append((current_point, p1, p3, p3))
                        current_point = p3
                    else:
                        stack.clear()
                else:
                    stack.append(token)
                    
        for child_xref in subject_items.get_form_xobject_xrefs(doc, xref):
            if child_xref not in seen:
                pending.append(child_xref)
    return curves

def point_in_rect(p, rect):
    x, y = p
    return rect.x0 <= x <= rect.x1 and rect.y0 <= y <= rect.y1

def curve_in_any_rect(curve, rects):
    """Checks if any control point of the curve falls inside any of the given rects."""
    for rect in rects:
        if any(point_in_rect(p, rect) for p in curve):
            return True
    return False

def process_page(args):
    """Multiprocessing worker to scan a single page for matching curves."""
    page_index, pdf_path, stamp_curves, stamp_rects_by_page, tolerance = args
    matched_curves = []
    
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    
    # Matches return 1-based page index, our dictionary uses 1-based index
    page_rects = stamp_rects_by_page.get(page_index + 1, [])
    
    drawings = page.get_drawings()
    
    for drawing in drawings:
        for item in drawing.get('items', []):
            if item[0] == 'c':
                # PyMuPDF cubic bezier: ('c', p1, p2, p3, p4)
                p0 = (item[1].x, item[1].y)
                p1 = (item[2].x, item[2].y)
                p2 = (item[3].x, item[3].y)
                p3 = (item[4].x, item[4].y)
                page_curve = (p0, p1, p2, p3)
                
                # Exclude curves that are part of stamp annotations
                if curve_in_any_rect(page_curve, page_rects):
                    continue
                
                # Check for a match against any of the extracted stamp curves
                for stamp_curve in stamp_curves:
                    if curves_match(page_curve, stamp_curve, tolerance):
                        matched_curves.append(page_curve)
                        break 
    
    doc.close()
    return page_index, matched_curves

def run_comprehensive_check():
    # 1. Load Configuration
    cfg = subject_items.load_config()
    input_folder = cfg["paths"]["input_folder"]
    output_folder = cfg["paths"].get("output_folder", os.path.join(input_folder, "edited samples"))
    targets = cfg.get("targets", [])
    
    # Fetch tolerance from config.json (length_tolerance is best for curve segment distances)
    tolerance = cfg.get("pattern_detection", {}).get("length_tolerance", 0.2)
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 2. Select PDF
    pdf_path = subject_items.select_pdf(input_folder)
    if not pdf_path:
        return

    print(subject_items.color_text(f"\n{'='*60}", subject_items.Ansi.BOLD))
    print(subject_items.color_text(f"COMPREHENSIVE PDF CURVE CHECKER: {os.path.basename(pdf_path)}", subject_items.Ansi.BOLD))
    print(subject_items.color_text(f"Tolerance: {tolerance}", subject_items.Ansi.CYAN))
    print(subject_items.color_text(f"{'='*60}", subject_items.Ansi.BOLD))

    # 3. Scan for Stamp Annotations
    print(subject_items.color_text("\n[STEP 1] Scanning for Stamp Annotations...", subject_items.Ansi.CYAN))
    matches, _ = subject_items.scan_pdf(pdf_path, targets)
    
    if not matches:
        print(subject_items.color_text("No stamp annotations matching your config targets were found.", subject_items.Ansi.RED))
        return
        
    print(f"Found {len(matches)} matching stamp(s).")

    # 4. Extract Curves from Stamps
    print(subject_items.color_text("\n[STEP 2] Extracting Curves from Stamps...", subject_items.Ansi.CYAN))
    
    doc = fitz.open(pdf_path)
    all_stamp_curves = []
    stamp_rects_by_page = {}
    
    for match in matches:
        page_num = match['page']
        rect = match['rect']
        target_name = match['target']
        
        if page_num not in stamp_rects_by_page:
            stamp_rects_by_page[page_num] = []
        stamp_rects_by_page[page_num].append(rect)
        
        # Access the annotation to parse its appearance stream
        page = doc[page_num - 1]
        annot_found = False
        for annot in page.annots() or []:
            norm_subj = subject_items.norm_text(annot.info.get("subject"))
            if annot.type[1] == "Stamp" and norm_subj == target_name:
                curves = parse_curves_from_annot(doc, annot)
                all_stamp_curves.extend(curves)
                print(f"Extracted {len(curves)} curves from {target_name} on page {page_num}")
                annot_found = True
                break
        
        if not annot_found:
            # Fallback to rect matching if subject didn't match perfectly
            for annot in page.annots() or []:
                if annot.type[1] == "Stamp" and abs(annot.rect.x0 - rect.x0) < 1.0 and abs(annot.rect.y0 - rect.y0) < 1.0:
                    curves = parse_curves_from_annot(doc, annot)
                    all_stamp_curves.extend(curves)
                    print(f"Extracted {len(curves)} curves from stamp on page {page_num} (matched by rect)")
                    break
                
    print(f"Extracted {len(all_stamp_curves)} curves from the grill stamps.")
    
    if not all_stamp_curves:
        print(subject_items.color_text("No curves found in the stamps. Exiting.", subject_items.Ansi.RED))
        doc.close()
        return

    # 5. Find Matches Across All Pages via Multiprocessing
    print(subject_items.color_text("\n[STEP 3] Detecting Matching Curves in Document...", subject_items.Ansi.CYAN))
    
    num_pages = len(doc)
    doc.close() # Close doc so multiprocessing workers can open it cleanly
    
    worker_args = [(i, pdf_path, all_stamp_curves, stamp_rects_by_page, tolerance) for i in range(num_pages)]
    all_matched_curves_by_page = {}
    total_matches = 0
    
    # Process each page in a separate CPU core
    with multiprocessing.Pool() as pool:
        for page_index, matched_curves in pool.imap_unordered(process_page, worker_args):
            all_matched_curves_by_page[page_index] = matched_curves
            total_matches += len(matched_curves)
            print(f"  Page {page_index + 1}: found {len(matched_curves)} matching curves.")

    print(subject_items.color_text(f"\nTotal matches found outside stamps: {total_matches}", subject_items.Ansi.BOLD))
    
    # 6. Color Matched Curves Red and Save PDF
    if total_matches > 0:
        print(subject_items.color_text("\n[STEP 4] Coloring Matched Curves Red and Saving...", subject_items.Ansi.CYAN))
        doc = fitz.open(pdf_path)
        
        for page_index, matched_curves in all_matched_curves_by_page.items():
            if not matched_curves:
                continue
                
            page = doc[page_index]
            for curve in matched_curves:
                p0, p1, p2, p3 = curve
                # Draw red curve overlay
                shape = page.new_shape()
                shape.draw_bezier(fitz.Point(*p0), fitz.Point(*p1), fitz.Point(*p2), fitz.Point(*p3))
                shape.finish(color=(1, 0, 0), width=1.5)
                shape.commit()
                
        output_filename = f"edited_{os.path.basename(pdf_path)}"
        output_path = os.path.join(output_folder, output_filename)
        
        doc.save(output_path)
        doc.close()
        
        print(subject_items.color_text(f"Saved to: {output_path}", subject_items.Ansi.GREEN))
        
        # Open in default editor
        try:
            os.startfile(output_path)
        except AttributeError:
            import subprocess
            subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', output_path])
    else:
        print(subject_items.color_text("No matched curves to save.", subject_items.Ansi.YELLOW))

if __name__ == "__main__":
    multiprocessing.freeze_support() # Good practice for Windows multiprocessing
    try:
        run_comprehensive_check()
    except Exception as e:
        print(subject_items.color_text(f"\nAn error occurred: {e}", subject_items.Ansi.RED))
        import traceback
        traceback.print_exc()
    input("\nPress Enter to exit...")

