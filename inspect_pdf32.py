import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]

drawings = page.get_drawings()
wipeout_idx = -1
text_idx = -1

for i, d in enumerate(drawings):
    # Wipeout around 894, 2150 (rotated, so checking unrotated coords)
    # The wipeouts we found were like Rect(895, 2151, 920, 2232)
    if d.get("fill") == (1.0, 1.0, 1.0) and d["rect"].x0 > 890 and d["rect"].x0 < 900 and d["rect"].y0 > 2140:
        wipeout_idx = i
        print(f"Found wipeout at index {i}: {d['rect']}")
    
    # Red text '25' is also around this area, with color (1.0, 0.0, 0.0)
    if d.get("color") == (1.0, 0.0, 0.0) and d["rect"].x0 > 890 and d["rect"].x0 < 910 and d["rect"].y0 > 2140:
        text_idx = i
        print(f"Found red stroke at index {i}: {d['rect']}")

print(f"Wipeout index: {wipeout_idx}, Text index: {text_idx}")
