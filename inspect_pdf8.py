import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
d = page.get_drawings()[22390]
print(f"White box: layer={d.get('layer')} stroke_opacity={d.get('stroke_opacity')} fill_opacity={d.get('fill_opacity')}")
