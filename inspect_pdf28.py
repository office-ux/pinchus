import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
clip = fitz.Rect(894, 2150, 921, 2233)
pix = page.get_pixmap(clip=clip, dpi=72)
# Count how many pure white pixels vs non-pure-white pixels
white = 0
non_white = 0
for y in range(pix.height):
    for x in range(pix.width):
        color = pix.pixel(x, y)
        if color == (255, 255, 255):
            white += 1
        else:
            non_white += 1

print(f"White pixels: {white}, Non-white pixels: {non_white}")
