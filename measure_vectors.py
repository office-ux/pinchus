import fitz
import os
import json
import math
from collections import Counter, defaultdict

def load_config(config_path="config.json"):
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except:
        return None

def measure():
    cfg = load_config()
    if not cfg:
        print("config.json not found.")
        return

    folder = cfg["paths"]["input_folder"]
    pdfs = [f for f in os.listdir(folder) if f.lower().endswith('.pdf')]
    
    if not pdfs:
        print(f"No PDFs in {folder}")
        return

    print("\nSelect a PDF to inspect line weights:")
    for i, f in enumerate(pdfs, 1):
        print(f"{i}. {f}")
    
    choice = input("\nEnter number: ")
    try:
        pdf_path = os.path.join(folder, pdfs[int(choice)-1])
    except:
        return

    doc = fitz.open(pdf_path)
    print(f"\nPDF Scale/Units:")
    # Check UserUnit (default is 1.0, which means 1 unit = 1/72 inch)
    user_unit = doc[0].read_contents() # Dummy to ensure page is loaded if needed
    # Better way to get UserUnit:
    page_num_input = input(f"Enter page number (1-{len(doc)}): ")
    try:
        p_idx = int(page_num_input)-1
        page = doc[p_idx]
    except:
        return

    # UserUnit is in the page dictionary
    u_unit = page.parent.xref_get_key(page.xref, "UserUnit")[1]
    if u_unit == "null":
        u_unit = 1.0
    else:
        u_unit = float(u_unit)
    
    print(f"  UserUnit: {u_unit} (1 unit = {u_unit * 72} points)")

    # --- INSPECT ANNOTATIONS ---
    print("\nPDF Annotations (Marks you drew):")
    annots = page.annots()
    annot_widths = defaultdict(int)
    found_annot = False
    for a in annots:
        # Border width is in a.border['width']
        b = a.border
        w = b.get('width', 0)
        subj = (a.info.get('subject') or "No Subject")
        annot_widths[(w, subj)] += 1
        found_annot = True
    
    if found_annot:
        for (w, subj), count in sorted(annot_widths.items()):
            print(f"  - Subject: '{subj:15}' | Border Width: {w:4} pt ({count} occurrences)")
    else:
        print("  - No annotations found.")

    drawings = page.get_drawings()
    print(f"\nFound {len(drawings)} drawing paths on Page {page_num_input}.")
    
    widths = set()
    lengths = []
    none_count = 0
    for d in drawings:
        w = d.get("width")
        if w is not None:
            widths.add(round(w, 4))
        else:
            none_count += 1
        
        for item in d["items"]:
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                l = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                lengths.append(round(l, 2))
            elif item[0] == "re":
                r = item[1]
                lengths.append(round(r.width, 2))
                lengths.append(round(r.height, 2))
    
    print("\nUnique line weights (widths) found (in pt):")
    if none_count > 0:
        print(f"  - (None) pt  ({none_count} occurrences)")
    for w in sorted(list(widths)):
        count = 0
        for d in drawings:
            d_w = d.get("width")
            if d_w is not None and round(d_w, 4) == w:
                count += 1
        print(f"  - {w} pt  ({count} occurrences)")

    print("\nCommon line lengths (top 10):")
    c = Counter(lengths)
    for l, count in c.most_common(10):
        print(f"  - {l} units  ({count} occurrences)")

    print("\nNote: Standard PDF points (1/72 inch).")
    
    target_w = input("\nEnter a specific dimension/width to find (e.g. 12): ").strip()
    if target_w:
        try:
            tw = float(target_w)
            found_any = False
            print(f"\nSearching for elements with width OR geometric dimension approx {tw} units...")
            for i, d in enumerate(drawings):
                # Check stroke width
                w = d.get("width")
                match_w = (w is not None and abs(w - tw) < 0.1)
                
                # Check geometric size of items in path
                match_geom = False
                for item in d["items"]:
                    if item[0] == "re":
                        r = item[1]
                        if abs(r.width - tw) < 0.1 or abs(r.height - tw) < 0.1:
                            match_geom = True; break
                    elif item[0] == "l":
                        p1, p2 = item[1], item[2]
                        l = math.hypot(p2[0]-p1[0], p2[1]-p1[1])
                        if abs(l - tw) < 0.1:
                            match_geom = True; break
                
                if match_w or match_geom:
                    r = d.get("rect")
                    type_str = "Stroke Width" if match_w else "Geometry"
                    print(f"  [{i}] {type_str}: {w if match_w else tw} units, Color: {d.get('color')}, Rect: {r}")
                    found_any = True
            if not found_any:
                print("  No elements found with that dimension.")
        except:
            print("Invalid input.")

if __name__ == "__main__":
    measure()
