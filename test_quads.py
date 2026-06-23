import sys
sys.path.insert(0, 'c:/pinchus')
import fitz
import detect_patterns as dp

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'
doc = fitz.open(pdf_path)
page = doc[0]
items = list(dp.iter_page_items(page))
polys = [i for i in items if i["shape_type"] == "polygon"]
print("Total page items:", len(items))
print("Polygon (qu) items on page:", len(polys))
for p in polys[:10]:
    print("  len=%.4f weight=%.3f color=%s pts=%s" % (
        p["length"], p["line_weight"],
        tuple(round(x,4) for x in p["stroke_color"]),
        [tuple(round(c,2) for c in pt) for pt in p["points"]]))
doc.close()
