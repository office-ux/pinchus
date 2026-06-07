import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]

clip = fitz.Rect(1785, 1083, 1811, 1165)
pix = page.get_pixmap(clip=clip, dpi=72)

black_pixels = 0
for y in range(pix.height):
    for x in range(pix.width):
        color = pix.pixel(x, y)
        if color[0] < 50 and color[1] < 50 and color[2] < 50:
            black_pixels += 1

print(f"Black pixels inside wipeout at 1785,1083: {black_pixels}")
