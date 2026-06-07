import fitz
doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]
a = fitz.Rect(100, 100, 140, 120)
print(f"Unrot width={a.width}, height={a.height}")
v = a * page.rotation_matrix
print(f"Visual width={v.width}, height={v.height}")
