import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
clip = fitz.Rect(894, 2150, 921, 2233)
pix = page.get_pixmap(clip=clip, dpi=72)
pix.save(r'C:\pinchus\wipeout_test.png')
print("Saved wipeout_test.png")
