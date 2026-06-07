import fitz

def test_explode():
    doc = fitz.open(r"c:\pinchus\Projects\test\pdfs\mechanical2.pdf")
    page = doc[0]
    
    a = [x for x in page.annots() if x.type[1]=='Stamp'][0]
    xref = a.xref
    
    # Get AP dictionary
    ap_val = doc.xref_get_key(xref, "AP")[1]
    if not ap_val.startswith("<<"):
        print("No AP dict")
        return
        
    import re
    m = re.search(r"/N\s+(\d+)\s+0\s+R", ap_val)
    if not m:
        print("No /N stream")
        return
        
    xobj_xref = int(m.group(1))
    
    bbox_str = doc.xref_get_key(xobj_xref, "BBox")[1]
    bbox_str = bbox_str.strip("[]")
    bx0, by0, bx1, by1 = map(float, bbox_str.split())
    
    # PDF native Rect from annot
    rect_str = doc.xref_get_key(xref, "Rect")[1]
    rect_str = rect_str.strip("[]")
    rx0, ry0, rx1, ry1 = map(float, rect_str.split())
    
    # PyMuPDF Rect vs Native Rect
    print("Native Rect:", rx0, ry0, rx1, ry1)
    print("Annot Rect:", a.rect)
    
    bw = bx1 - bx0
    bh = by1 - by0
    rw = rx1 - rx0
    rh = ry1 - ry0
    
    sx = rw / bw if bw else 1.0
    sy = rh / bh if bh else 1.0
    
    ex = rx0 - bx0 * sx
    ey = ry0 - by0 * sy
    
    name = f"FmStamp{xref}"
    page.clean_contents()
    doc.xref_set_key(page.xref, f"Resources/XObject/{name}", f"{xobj_xref} 0 R")
    
    contents_xref = page.get_contents()[0]
    
    cmd = f"\nq\n{sx:g} 0 0 {sy:g} {ex:g} {ey:g} cm\n/{name} Do\nQ\n"
    
    stream = doc.xref_stream(contents_xref)
    doc.update_stream(contents_xref, stream + cmd.encode('latin1'))
    
    page.delete_annot(a)
    doc.save('test_explode.pdf')
    print("Exploded and saved to test_explode.pdf")

test_explode()
