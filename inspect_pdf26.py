import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
for xref in page.get_xobjects():
    # xref is (xref_num, name, type)
    if xref[2] == 'form':
        # Check its ExtGState
        xobj_stream = doc.xref_stream(xref[0])
        print(f"Form XObject {xref[0]} ({xref[1]}): length {len(xobj_stream) if xobj_stream else 0}")
