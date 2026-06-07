import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
text_instances = page.search_for("SD1")
if text_instances:
    rect = text_instances[0]
    print(f"Found SD1 at {rect}")
    drawings = page.get_drawings()
    for i, d in enumerate(drawings):
        d_rect = d.get('rect')
        if d_rect and rect.intersects(d_rect):
            print(f"Intersecting drawing {i}: color={d.get('color')} fill={d.get('fill')}")
