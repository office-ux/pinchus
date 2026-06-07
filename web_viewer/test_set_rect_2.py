import fitz

doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]

annot = page.add_freetext_annot(fitz.Rect(100, 100, 200, 200), "Test", fontsize=10)
annot.update()
doc.xref_set_key(annot.xref, "StampID", "(test_uuid)")
doc.save(r"C:\pinchus\web_viewer\test_set_rect_pre.pdf")
doc.close()

doc = fitz.open(r"C:\pinchus\web_viewer\test_set_rect_pre.pdf")
page = doc[0]
a = list(page.annots())[-1]
print("Before set_rect StampID:", doc.xref_get_key(a.xref, "StampID"))
a.set_rect(fitz.Rect(300, 300, 400, 400))
print("After set_rect StampID:", doc.xref_get_key(a.xref, "StampID"))

# Now let's try just setting the Rect directly via PyMuPDF's Rect conversion:
# Wait, if we use fitz.Rect for visual coordinates, how do we convert it to raw unrotated bottom-left?
# Let's do it manually:
vis_rect = fitz.Rect(500, 500, 600, 600)
# We want the unrotated coordinates. We know the page cropbox.
# But set_rect is so much easier.
