import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]

annot_rect = fitz.Rect(894, 2150, 921, 2233)
print(f"Annot rect: {annot_rect}")

paths_found = 0
for d in page.get_drawings():
    if d["rect"].intersects(annot_rect):
        paths_found += 1

print(f"Paths in get_drawings near annot: {paths_found}")

# Also let's check what's inside the annotation itself!
for a in page.annots():
    if a.rect.intersects(annot_rect):
        print(f"Annot type: {a.type}, subtype: {a.info.get('subject')}")
