import sys
sys.path.insert(0, 'c:/pinchus')
import fitz
import detect_patterns as dp
import detect_subject_items as si

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'
doc = fitz.open(pdf_path)
page = doc[0]

matches, _ = si.load_pdf_pattern_matches(pdf_path)
# Arc-based Supply match (page 1, 13 segs)
arc_match = next(m for m in matches if m["page"]==1 and m["line_count"]==13)

print("Arc match target:", arc_match["target"])
print("Arc segments (first 3):")
for seg in arc_match["segments"][:3]:
    print("  shape=%s start=%s end=%s len=%.4f" % (
        seg["shape_type"], 
        tuple(round(x,2) for x in seg["start"]),
        tuple(round(x,2) for x in seg["end"]),
        seg["length"]))

# Find matching arcs on the page at those exact coords
page_items = list(dp.iter_page_items(page))
arcs = [i for i in page_items if i["shape_type"] == "arc"]
print("\nPage arcs near first arc segment start (883.13, 992.86):")
for arc in arcs:
    sx, sy = arc["start"]
    if abs(sx - 883.13) < 5 and abs(sy - 992.86) < 5:
        print("  FOUND arc: len=%.4f color=%s weight=%.3f" % (
            arc["length"], tuple(round(x,4) for x in arc["stroke_color"]), arc["line_weight"]))
        print("  start=%s end=%s" % (arc["start"], arc["end"]))

print("\n=== Key insight: do arc coords in JSON match page drawing coords? ===")
json_start = (883.1279296875, 992.8612060546875)
for arc in arcs[:5]:
    print("  page arc start=%s" % (arc["start"],))
