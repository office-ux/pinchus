import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
for block in page.get_text("dict")["blocks"]:
    if "lines" in block:
        for line in block["lines"]:
            for span in line["spans"]:
                if "575" in span["text"]:
                    print(f"Found '575' at {span['bbox']}")
                if "PD" in span["text"]:
                    print(f"Found 'PD' at {span['bbox']}")
