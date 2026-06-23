import sys
sys.path.insert(0, 'c:/pinchus')
import fitz

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'
doc = fitz.open(pdf_path)
page = doc[0]

# PDF page size
rect = page.rect
print("PDF page rect:", rect)
print("PDF width:", rect.width, "height:", rect.height)

# Canvas coords from pattern JSON
canvas_pts = [(997.26, 1044.3), (1011.06, 1011), (1007.76, 1009.68), (993.96, 1042.92)]
print("\nCanvas polygon points:", canvas_pts)

# What are the actual drawings at those coordinates (no scaling)?
import detect_patterns as dp
items = list(dp.iter_page_items(page))

# Find the single line we found near (997,1044) etc
print("\n=== Looking with 10pt tolerance ===")
for item in items:
    sx, sy = item["start"]
    ex, ey = item["end"]
    for tx, ty in canvas_pts:
        if (abs(sx-tx) < 10 and abs(sy-ty) < 10) or (abs(ex-tx) < 10 and abs(ey-ty) < 10):
            print("  MATCH: shape=%s len=%.2f start=(%.2f,%.2f) end=(%.2f,%.2f) color=%s" % (
                item["shape_type"], item["length"],
                sx, sy, ex, ey,
                tuple(round(x,4) for x in item["stroke_color"])))
            break

# What if coordinates need to be scaled? 
# Try finding the shape by searching for 4 connected lines making a parallelogram
print("\n=== All lines with color (0.969, 0.671, 0.682) ===")
pink_lines = [i for i in items if i["shape_type"] == "line" and
              abs(i["stroke_color"][0] - 0.96863) < 0.01 and
              abs(i["stroke_color"][1] - 0.67059) < 0.01 and
              abs(i["stroke_color"][2] - 0.68235) < 0.01]
print("Count:", len(pink_lines))
for item in pink_lines[:10]:
    print("  len=%.4f start=(%.2f,%.2f) end=(%.2f,%.2f)" % (
        item["length"], item["start"][0], item["start"][1],
        item["end"][0], item["end"][1]))

doc.close()
