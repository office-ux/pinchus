import fitz

doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]

annot = page.add_freetext_annot(fitz.Rect(100, 100, 200, 200), "Test", fontsize=10)
# Now move it using set_rect
annot.set_rect(fitz.Rect(300, 300, 400, 400))
print("Raw Rect after set_rect:", doc.xref_get_key(annot.xref, "Rect"))

doc.save(r"C:\pinchus\web_viewer\test_set_rect.pdf")
print("Saved to test_set_rect.pdf")
