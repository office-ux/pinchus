import fitz

doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]

# Add annotation in unrotated coords
unrot = fitz.Rect(100, 100, 200, 200)
a = page.add_freetext_annot(unrot, "UNROT", fontsize=10, fill_color=(1,0,0))
a.update()

# Add annotation in visual coords
vis = fitz.Rect(100, 100, 200, 200) * page.rotation_matrix
b = page.add_freetext_annot(vis, "VIS", fontsize=10, fill_color=(0,1,0))
b.update()

doc.save(r"C:\pinchus\web_viewer\test_add_freetext.pdf")
