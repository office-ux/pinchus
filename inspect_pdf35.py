import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
drawings = page.get_drawings()

wipeout = None
for i, d in enumerate(drawings):
    if d.get("fill") == (1.0, 1.0, 1.0) and d["rect"].x0 > 890 and d["rect"].x0 < 900 and d["rect"].y0 > 2140:
        wipeout = d
        print(f"Wipeout at index {i}: {d['rect']}")
        break

if wipeout:
    rect = wipeout["rect"]
    for i, d in enumerate(drawings):
        if d["rect"].intersects(rect) and i != 22438:
            print(f"Intersection at index {i}, color: {d.get('color')}, fill: {d.get('fill')}")
