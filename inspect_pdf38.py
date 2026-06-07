import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
drawings = page.get_drawings()

search_rect = fitz.Rect(850, 2130, 950, 2250)

print("Paths in search rect:")
for i, d in enumerate(drawings):
    if d["rect"].intersects(search_rect):
        print(f"Index {i}: color={d.get('color')}, fill={d.get('fill')}, rect={d['rect']}")
