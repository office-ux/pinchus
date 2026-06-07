import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
found = False
for block in page.get_text("dict")["blocks"]:
    if "lines" in block:
        for line in block["lines"]:
            for span in line["spans"]:
                if "SD1" in span["text"]:
                    print(f"Found 'SD1' as text at {span['bbox']}")
                    found = True
if not found:
    print("'SD1' is NOT text!")
