import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
for i, d in enumerate(page.get_drawings()[:10]):
    print(f"Drawing {i}: color={d.get('color')} fill={d.get('fill')} blend_mode={d.get('blend_mode', 'Normal')}")
