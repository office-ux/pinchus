import fitz

pdf_path = r"c:\pinchus\Projects\123\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf"
doc = fitz.open(pdf_path)
found = False
print(f"Total pages: {len(doc)}")
for page_num in range(len(doc)):
    page = doc[page_num]
    for annot in page.annots() or []:
        if annot.type[1] == "Stamp":
            name = annot.info.get("name")
            xref = annot.xref
            if name == "39752c07-8007-4c95-bae5-ab63102a9134" or not found:
                print(f"Page {page_num+1}: Stamp Name={name}, Xref={xref}, Info={annot.info}")
                if name == "39752c07-8007-4c95-bae5-ab63102a9134":
                    found = True
                    break
    if found:
        break
doc.close()
