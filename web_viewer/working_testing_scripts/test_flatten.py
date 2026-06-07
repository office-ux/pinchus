import fitz

def test_flatten():
    doc = fitz.open(r"c:\pinchus\Projects\test\pdfs\mechanical2.pdf")
    page = doc[0]
    
    # find stamp
    annot_to_flatten = None
    for a in page.annots():
        if a.type[1] == "Stamp":
            annot_to_flatten = a
            break
            
    if annot_to_flatten:
        print("Found stamp!", annot_to_flatten.xref)
        # Check if it has an appearance stream
        print("AP dictionary:", doc.xref_get_key(annot_to_flatten.xref, "AP"))
        
        # Does PyMuPDF have an explicit way to flatten?
        # Let's check help for annot
        import types
        methods = [m for m in dir(annot_to_flatten) if not m.startswith('_')]
        print("Methods:", methods)
    else:
        print("No stamp found")
        
test_flatten()
