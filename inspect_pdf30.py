import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
clip = fitz.Rect(894, 2150, 921, 2233)
pix = page.get_pixmap(clip=clip, dpi=72)
pixels = []
for y in range(pix.height):
    for x in range(pix.width):
        color = pix.pixel(x, y)
        if color != (255, 255, 255):
            pixels.append(color)

print(f"Non-white pixels count: {len(pixels)}")
if len(pixels) > 0:
    print(f"Sample non-white pixels: {pixels[:20]}")
