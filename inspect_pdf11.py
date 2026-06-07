import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
pix_rgb = page.get_pixmap(colorspace=fitz.csRGB, dpi=72)
pix_cmyk = page.get_pixmap(colorspace=fitz.csCMYK, dpi=72)
print("RGB alpha:", pix_rgb.alpha)
print("CMYK alpha:", pix_cmyk.alpha)
# Let's check a pixel in the white box!
# White box 25 is around 320, 1480 (from our text search).
# Since dpi=72, coordinates are exactly 320, 1480.
color_rgb = pix_rgb.pixel(320, 1480)
color_cmyk = pix_cmyk.pixel(320, 1480)
print(f"RGB pixel: {color_rgb}")
print(f"CMYK pixel: {color_cmyk}")
