import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
drawings = page.get_drawings()

wipeout = None
for i, d in enumerate(drawings):
    if d.get("fill") == (1.0, 1.0, 1.0) and d["rect"].x0 > 1780 and d["rect"].x0 < 1790:
        wipeout = d
        print(f"Wipeout at index {i}: {d['rect']}")
        break

if wipeout:
    rect = wipeout["rect"]
    # Find any strokes that intersect this rect
    for i, d in enumerate(drawings):
        if d["rect"].intersects(rect) and i != 22438:
            print(f"Intersection at index {i}, color: {d.get('color')}, fill: {d.get('fill')}")
