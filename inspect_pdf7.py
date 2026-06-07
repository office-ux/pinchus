import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
drawings = page.get_drawings()
for i, d in enumerate(drawings):
    c = d.get('color')
    if c and len(c) == 3 and c[0] > c[1] + c[2]:
        print(f"Red drawing {i}: color={c} fill={d.get('fill')}")
