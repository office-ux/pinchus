import fitz
doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]
print(f"Rotation: {page.rotation}")
print(f"rect: {page.rect}")
print(f"cropbox: {page.cropbox}")
print(f"mediabox: {page.mediabox}")
