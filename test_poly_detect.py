import sys
sys.path.insert(0, 'c:/pinchus')
import fitz
import detect_subject_items as si
import detect_patterns as dp
import detect_matching_lines as ml

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'

# Load the polygon pattern signature (Supply, page 1, line segments)
matches, _ = si.load_pdf_pattern_matches(pdf_path)
# Pick the polygon one (4 line segs, short lengths ~36/3.5)
poly_matches = [m for m in matches if m["type"] == "grill" and m["page"] == 1
                and m["line_count"] == 4 and m["segments"][0]["shape_type"] == "line"]
print("Polygon-based matches:", len(poly_matches))
for m in poly_matches:
    print(" target=%s lengths=%s" % (m["target"], [round(l,2) for l in m["lengths"]]))

# Build signatures from those
signatures = dp.get_unique_signatures(poly_matches)
print("\nSignatures:", len(signatures))
for s in signatures[:4]:
    print("  angle=%s width=%.2f height=%.2f" % (s["angle"], s["width"], s["height"]))
    for seg in s["segments"]:
        print("    shape=%s len=%.2f start_rel=%s end_rel=%s" % (
            seg["shape_type"], seg["length"],
            tuple(round(x,2) for x in seg["start_rel"]),
            tuple(round(x,2) for x in seg["end_rel"])))

# Now scan page 1 for matching items
doc = fitz.open(pdf_path)
page = doc[0]
page_items = list(dp.iter_page_items(page))
print("\nTotal page items:", len(page_items))
print("Lines:", sum(1 for i in page_items if i["shape_type"] == "line"))
print("Rects:", sum(1 for i in page_items if i["shape_type"] == "rect"))
print("Arcs:", sum(1 for i in page_items if i["shape_type"] == "arc"))

# Get scan config
import json
with open(r'c:/pinchus/config.json') as f:
    cfg = json.load(f)
scan_cfg = ml.get_scan_config(cfg)
print("\nScan config:", scan_cfg)

# Filter items matching any signature segment
filtered = []
for item in page_items:
    for sig in signatures:
        for s in sig["segments"]:
            if item["shape_type"] != s.get("shape_type", "line"):
                continue
            if abs(item["length"] - s["length"]) > scan_cfg["length_tolerance"]:
                continue
            if abs(item["line_weight"] - s["line_weight"]) > scan_cfg["line_weight_tolerance"]:
                continue
            if not ml.colors_match(item["stroke_color"], s["stroke_color"], scan_cfg["color_tolerance"]):
                continue
            filtered.append(item)
            break
        else:
            continue
        break

print("\nFiltered items (potential matches):", len(filtered))
for item in filtered[:10]:
    print("  shape=%s len=%.2f weight=%.2f color=%s" % (
        item["shape_type"], item["length"], item["line_weight"], item["stroke_color"]))

doc.close()
