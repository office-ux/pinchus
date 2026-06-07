import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=150)
pix.save(r'C:\pinchus\test_render.png')
print("Rendered test_render.png")
