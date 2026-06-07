import fitz

doc = fitz.open()
page = doc.new_page(width=100, height=200)

# Draw a distinct black pixel line at unrotated (20, 20) -> (20, 30)
page.draw_line(fitz.Point(20, 20), fitz.Point(20, 30), color=(0, 0, 0), width=1)

# Rotate 270 degrees. Rotated rect width=200, height=100.
page.set_rotation(270)

# Transform point (20, 20) using rotation_matrix
m = page.rotation_matrix
p_trans = fitz.Point(20, 20) * m
print('Transformed point:', p_trans)

# Render page to pixmap
pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))

# Find the black pixel in the pixmap
black_pixels = []
for y in range(pix.height):
    for x in range(pix.width):
        idx = (y * pix.width + x) * pix.n
        r, g, b = pix.samples[idx:idx+3]
        if r < 50 and g < 50 and b < 50:
            black_pixels.append((x, y))

print('Black pixels found in rendered image:', black_pixels)
doc.close()
