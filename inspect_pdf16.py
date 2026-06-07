import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
pix_rgb = page.get_pixmap(colorspace=fitz.csRGB, dpi=72)

# Wipeout for red '25' is approx Rect(894, 2150, 921, 2233)
# Let's check a column of pixels to see if any black line crosses it
for y in range(2150, 2233):
    color = pix_rgb.pixel(900, y)
    if color[0] < 50 and color[1] < 50 and color[2] < 50:
        print(f"Found BLACK pixel at 900, {y}")
        break
else:
    print("No black line found passing through x=900 inside the wipeout.")
