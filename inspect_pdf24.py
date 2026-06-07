import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]

# Let's find a wipeout and print its raw PDF operator or graphic state
wipeouts = []
for d in page.get_drawings():
    if d.get("fill") == (1.0, 1.0, 1.0) or d.get("fill") == [1.0, 1.0, 1.0]:
        wipeouts.append(d)

print("Found wipeouts:", len(wipeouts))
if wipeouts:
    w = wipeouts[0]
    print("Wipeout rect:", w["rect"])
    print("Wipeout layer:", w.get("layer"))
    print("Wipeout fill_opacity:", w.get("fill_opacity"))
    print("Wipeout stroke_opacity:", w.get("stroke_opacity"))
    print("Wipeout blend_mode:", w.get("blend_mode"))
    print("Wipeout extgstate:", w.get("extgstate"))
