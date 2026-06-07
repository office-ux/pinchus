import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
drawings = page.get_drawings()

wipeout_rect = fitz.Rect(894.2, 2150.6, 921.2, 2233.9)

for i, d in enumerate(drawings):
    if d["rect"].intersects(wipeout_rect) and i < 22438:
        # Don't print the black lines (they have color None or black and no fill)
        if d.get("color") != (0.0, 0.0, 0.0):
            print(f"Path before wipeout at index {i}: color={d.get('color')}, rect={d['rect']}")
