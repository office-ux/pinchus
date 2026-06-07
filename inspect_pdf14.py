import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]

wipeouts = []
for d in page.get_drawings():
    if d.get("fill") == (1.0, 1.0, 1.0) or d.get("fill") == [1.0, 1.0, 1.0]:
        wipeouts.append(d["rect"])

for r in wipeouts:
    print(r)
