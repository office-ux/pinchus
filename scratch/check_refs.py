import fitz

def check_references(pdf_path, xrefs_to_check):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        print(f"Page {page_num + 1} references:")
        # Check resources
        res = page.get_contents()
        # This is hard. Easier to check page.get_xobjects()
        for x in page.get_xobjects():
            if x[0] in xrefs_to_check:
                print(f"  - References stamp XREF {x[0]} (Name: {x[1]})")
    doc.close()

if __name__ == "__main__":
    pdf_path = r"c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309..pdf"
    check_references(pdf_path, [38, 39, 40, 41, 42, 43])
