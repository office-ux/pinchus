import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
for i, d in enumerate(page.get_drawings()[:50]):
    if d.get('color') == (1.0, 0.0, 0.0) or d.get('fill') == (1.0, 1.0, 1.0):
        print(f"Drawing {i}: color={d.get('color')} fill={d.get('fill')} blend_mode={d.get('blend_mode', 'Normal')}")
