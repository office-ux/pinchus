import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=72)
# The wipeout is around 894, 2150 to 921, 2233
# Let's print a small 20x20 region inside it
# We'll print ' ' for white, '.' for light gray, '#' for dark/black, 'R' for red
print("ASCII Map:")
for y in range(2150, 2170):
    row = ""
    for x in range(894, 921):
        try:
            color = pix.pixel(x, y)
            if color == (255, 255, 255):
                row += " "
            elif color[0] > 200 and color[1] < 100 and color[2] < 100:
                row += "R" # Red
            elif color[0] < 100 and color[1] < 100 and color[2] < 100:
                row += "#" # Black/Dark
            else:
                row += "." # Gray/Other
        except:
            row += "?"
    print(row)
