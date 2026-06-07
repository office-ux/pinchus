import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
for pno in range(len(doc)):
    page = doc[pno]
    for block in page.get_text("dict")["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    if "SD1" in span["text"]:
                        print(f"Page {pno}: Found 'SD1' as text at {span['bbox']}")
