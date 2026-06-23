import sys
sys.path.insert(0, 'c:/pinchus')
import fitz
import detect_patterns as dp
import detect_matching_lines as ml

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'
doc = fitz.open(pdf_path)
page = doc[0]

sig_color = (0.9686300158500671, 0.6705899834632874, 0.6823499798774719)
sig_lengths = [36.05, 3.55, 35.99, 3.58]
sig_weight = 0.72

print("Signature color:", sig_color)
print("Signature weight:", sig_weight)

page_items = list(dp.iter_page_items(page))

print("\n=== Lines matching length (tol=0.25) AND weight (tol=0.25) ===")
matched = []
for item in page_items:
    if item["shape_type"] != "line":
        continue
    if not any(abs(item["length"] - tl) < 0.25 for tl in sig_lengths):
        continue
    if abs(item["line_weight"] - sig_weight) > 0.25:
        continue
    matched.append(item)
    diff = tuple(abs(item["stroke_color"][i] - sig_color[i]) for i in range(3))
    print("  len=%.4f weight=%.3f color=%s  color_diff=%s" % (
        item["length"], item["line_weight"],
        tuple(round(x,6) for x in item["stroke_color"]),
        tuple(round(x,6) for x in diff)))

print("\nTotal:", len(matched))
doc.close()
