import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
fills = set()
for d in page.get_drawings():
    f = d.get("fill")
    if f is not None:
        fills.add(f)
print("Unique fill colors found in drawings:")
for f in fills:
    print(f)
