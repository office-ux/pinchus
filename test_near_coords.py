import sys
sys.path.insert(0, 'c:/pinchus')
import fitz
import detect_patterns as dp

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'
doc = fitz.open(pdf_path)
page = doc[0]

# The polygon saved coords: (997.26, 1044.3), (1011.06, 1011), (1007.76, 1009.68), (993.96, 1042.92)
# Look for page drawings near those coords
target_pts = [(997.26, 1044.3), (1011.06, 1011), (1007.76, 1009.68), (993.96, 1042.92)]

page_items = list(dp.iter_page_items(page))
print("=== All lines near the polygon coords (within 5pt) ===")
found = []
for item in page_items:
    sx, sy = item["start"]
    ex, ey = item["end"]
    # Check if start or end is near any target point
    for tx, ty in target_pts:
        if (abs(sx - tx) < 5 and abs(sy - ty) < 5) or (abs(ex - tx) < 5 and abs(ey - ty) < 5):
            found.append(item)
            break

for item in found:
    print("  shape=%s len=%.4f weight=%.4f color=%s" % (
        item["shape_type"], item["length"], item["line_weight"],
        tuple(round(x, 5) for x in item["stroke_color"])))

# Also check rects near those coords
print("\n=== All rects on the page near those coords ===")
for item in page_items:
    if item["shape_type"] != "rect":
        continue
    rx, ry = item["start"]
    if abs(rx - 993) < 30 and abs(ry - 1011) < 50:
        print("  rect x=%.2f y=%.2f w=%.2f h=%.2f color=%s" % (
            item["x"], item["y"], item["width"], item["height"],
            tuple(round(x,5) for x in item["stroke_color"])))

doc.close()
