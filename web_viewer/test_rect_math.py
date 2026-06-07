import fitz
doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]
print("Page rot:", page.rotation)
vis_rect = fitz.Rect(80, 90, 120, 110)
unrot = vis_rect * ~page.rotation_matrix
print("Vis:", vis_rect)
print("Unrot:", unrot)
