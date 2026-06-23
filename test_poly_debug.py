import sys
sys.path.insert(0, 'c:/pinchus')
import fitz
import detect_patterns as dp
import detect_matching_lines as ml

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'
doc = fitz.open(pdf_path)
page = doc[0]

# What are the signature lengths/colors we're looking for?
# Supply polygon: lengths ~36.05, 3.55, 35.99, 3.58 | color (0.9686, 0.6706, 0.6824) | weight 0.72

# Find page lines with length close to 36 or 3.5
target_lens = [36.05, 3.55, 35.99, 3.58]
tol = 5.0  # relax tolerance a lot to find candidates

print("=== Page lines with length near 36 or 3.5 (tol=5.0) ===")
page_items = list(dp.iter_page_items(page))
candidates = []
for item in page_items:
    if item["shape_type"] != "line":
        continue
    if any(abs(item["length"] - tl) < tol for tl in target_lens):
        candidates.append(item)

print("Candidate count:", len(candidates))
# Show unique colors and weights
colors_seen = set()
weights_seen = set()
for c in candidates:
    colors_seen.add(tuple(round(x,4) for x in c["stroke_color"]))
    weights_seen.add(round(c["line_weight"],3))

print("Colors seen:", list(colors_seen)[:20])
print("Weights seen:", sorted(weights_seen)[:20])

# Now show lines with EXACTLY the right length range (0.25 tol)
print("\n=== With tight length tolerance 0.25 ===")
tight = [i for i in candidates if any(abs(i["length"] - tl) < 0.25 for tl in target_lens)]
print("Count:", len(tight))
for item in tight[:10]:
    print("  len=%.4f weight=%.3f color=%s" % (
        item["length"], item["line_weight"],
        tuple(round(x,4) for x in item["stroke_color"])))

doc.close()
