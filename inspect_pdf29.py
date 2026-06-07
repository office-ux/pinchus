import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
for d in page.get_drawings():
    if d.get("color") == (1.0, 0.0, 0.0):
        print(f"Red stroke found at: {d['rect']}")
