import fitz

def search_xobjects(pdf_path):
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        xobjs = page.get_images() + page.get_xobjects()
        if xobjs:
            # get_xobjects returns a list of (xref, name, type, ...)
            # page.get_xobjects() might not be directly available in all versions, 
            # let's use a more robust way to find XObjects
            pass
        
        # Alternative: iterate through all objects in the PDF
        for xref in range(1, doc.xref_length()):
            obj_name = doc.xref_get_key(xref, "Name")
            if obj_name[0] != "0" and "Stamp" in obj_name[1]:
                 print(f"Found object with 'Stamp' in name: XREF {xref}, Name: {obj_name[1]}")
            
            # Check Subtype
            subtype = doc.xref_get_key(xref, "Subtype")
            if subtype[1] == "/Stamp":
                print(f"Found object with Subtype /Stamp: XREF {xref}")

    doc.close()

if __name__ == "__main__":
    pdf_path = r"c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309..pdf"
    search_xobjects(pdf_path)
