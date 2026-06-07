import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
drawings = page.get_drawings()

wipeout_rect = fitz.Rect(894.2, 2150.6, 921.2, 2233.9)

for i, d in enumerate(drawings):
    if d["rect"].intersects(wipeout_rect) and i < 22438:
        # Check if it's the black line or something else
        # The black line we found earlier was at 15062-15073
        if i > 15073:
            print(f"Path between black line and wipeout: index {i}, color={d.get('color')}, rect={d['rect']}")
