import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
for annot in page.annots():
    if annot.type[0] == fitz.PDF_ANNOT_STAMP:
        print(f"Found Stamp annot at: {annot.rect}")
