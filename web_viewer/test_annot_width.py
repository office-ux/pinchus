import fitz
doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]
for a in page.annots():
    print(f"Annot: {a.rect}, width={a.rect.width}, height={a.rect.height}")
    v = a.rect * page.rotation_matrix
    print(f"Visual: {v}, width={v.width}, height={v.height}")
