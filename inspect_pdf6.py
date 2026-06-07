import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
drawings = page.get_drawings()
print(f"Total drawings: {len(drawings)}")
for i, d in enumerate(drawings):
    fill = d.get('fill')
    if fill:
        # Check if fill is white (all components are 1.0)
        if all(x >= 0.99 for x in fill):
            print(f"Drawing {i}: color={d.get('color')} fill={fill} rect={d.get('rect')}")
