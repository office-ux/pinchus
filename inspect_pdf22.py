import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=72)
print("ASCII Map:")
for y in range(2130, 2160):
    row = ""
    for x in range(894, 921):
        color = pix.pixel(x, y)
        if color == (255, 255, 255):
            row += " "
        elif color[0] > 200 and color[1] < 100 and color[2] < 100:
            row += "R"
        elif color[0] < 100 and color[1] < 100 and color[2] < 100:
            row += "#"
        else:
            row += "."
    print(row)
