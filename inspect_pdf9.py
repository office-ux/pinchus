import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
for block in page.get_text("dict")["blocks"]:
    if "lines" in block:
        for line in block["lines"]:
            for span in line["spans"]:
                if span["text"].strip() in ["25", "26", "28"]:
                    print(f"Text '{span['text']}' color={hex(span['color'])} bbox={span['bbox']}")
