import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
pix = page.get_pixmap(dpi=72)
matching_wipeout = fitz.Rect(894.2, 2150.6, 921.2, 2233.9)
x0 = int(matching_wipeout.x0)
y0 = int(matching_wipeout.y0)
x1 = int(matching_wipeout.x1)
y1 = int(matching_wipeout.y1)
black_pixels = 0
for y in range(y0, y1):
    for x in range(x0, x1):
        try:
            color = pix.pixel(x, y)
            if color[0] < 50 and color[1] < 50 and color[2] < 50:
                black_pixels += 1
        except:
            pass
print(f"Without clean_contents: Black pixels inside wipeout={black_pixels}")
