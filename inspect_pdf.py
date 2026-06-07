import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
print('Drawings:')
drawings = page.get_drawings()
for i, d in enumerate(drawings[:20]):
    print(f'Drawing {i}: color={d.get("color")} fill={d.get("fill")} stroke_opacity={d.get("stroke_opacity")} fill_opacity={d.get("fill_opacity")}')
print('Annots:')
for annot in page.annots():
    print(annot.type, annot.info)
