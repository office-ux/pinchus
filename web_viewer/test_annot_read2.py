import fitz
doc = fitz.open(r"C:\pinchus\web_viewer\test_add_freetext.pdf")
page = doc[0]
for annot in page.annots():
    print(annot.info.get("content", ""), ":", annot.rect)
