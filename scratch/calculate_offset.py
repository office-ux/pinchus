import fitz

doc = fitz.open('Sample pdfs/Drrwaings samples/mechanical2.pdf')
page = doc[0]

# Render page at scale 1.0 (no scale)
pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))

# Search for the U-shape in the image around x in [1200, 1500], y in [400, 600]
# We look for grey/black pixels (any channel < 100)
x_min, x_max = 1200, 1500
y_min, y_max = 400, 600

drawn_pixels = []
for y in range(y_min, y_max):
    for x in range(x_min, x_max):
        idx = (y * pix.width + x) * pix.n
        r, g, b = pix.samples[idx:idx+3]
        if r < 100 and g < 100 and b < 100:
            drawn_pixels.append((x, y))

if drawn_pixels:
    xs = [p[0] for p in drawn_pixels]
    ys = [p[1] for p in drawn_pixels]
    print(f'Rendered U-shape bounds: x range [{min(xs)}, {max(xs)}], y range [{min(ys)}, {max(ys)}]')
else:
    print('No pixels found in the specified range.')

# Let's print the vector coordinates of drawing 30098 rotated:
d = page.get_drawings()[30098]
m = page.rotation_matrix
pts_trans = [p * m for p in d['items'][0][1:]]
xs_vec = [p.x for p in pts_trans]
ys_vec = [p.y for p in pts_trans]
print(f'Vector U-shape bounds: x range [{min(xs_vec)}, {max(xs_vec)}], y range [{min(ys_vec)}, {max(ys_vec)}]')

doc.close()
