import fitz
doc = fitz.open(r"C:\pinchus\web_viewer\test_add_freetext.pdf")
page = doc[0]
for a in page.annots():
    print(f"Annot: {a.rect}, width={a.rect.width}, height={a.rect.height}")
    v = a.rect * page.rotation_matrix
    print(f"Visual: {v}, width={v.width}, height={v.height}")
