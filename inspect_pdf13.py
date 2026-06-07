import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]

wipeouts = []
for d in page.get_drawings():
    if d.get("fill") == (1.0, 1.0, 1.0) or d.get("fill") == [1.0, 1.0, 1.0]:
        wipeouts.append(d["rect"])

print(f"Total wipeouts found: {len(wipeouts)}")
text_25_rect = fitz.Rect(316.6, 1476.5, 323.9, 1484.4)

matching_wipeout = None
for r in wipeouts:
    if r.contains(text_25_rect) or text_25_rect.intersects(r):
        matching_wipeout = r
        print(f"Found wipeout for '25': {r}")

if matching_wipeout:
    pix = page.get_pixmap(dpi=72)
    x0 = int(matching_wipeout.x0)
    y0 = int(matching_wipeout.y0)
    x1 = int(matching_wipeout.x1)
    y1 = int(matching_wipeout.y1)
    black_pixels = 0
    red_pixels = 0
    other_pixels = 0
    for y in range(y0, y1):
        for x in range(x0, x1):
            color = pix.pixel(x, y)
            if color[0] < 50 and color[1] < 50 and color[2] < 50:
                black_pixels += 1
            elif color[0] > 200 and color[1] < 50 and color[2] < 50:
                red_pixels += 1
            elif color != (255, 255, 255):
                other_pixels += 1
    print(f"Inside wipeout: Black pixels={black_pixels}, Red pixels={red_pixels}, Other non-white={other_pixels}")
