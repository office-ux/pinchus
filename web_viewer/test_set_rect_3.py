import fitz
doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]

annot = page.add_freetext_annot(fitz.Rect(100, 100, 140, 120), "Test")
annot.set_rect(fitz.Rect(100, 100, 140, 120))

print("Raw Rect:", doc.xref_get_key(annot.xref, "Rect"))
print("Annot Rect:", annot.rect)
