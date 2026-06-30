import os
import fitz
import re

def test_composite(pdf_path, xref, base_shape, global_stamps_dir):
    doc = fitz.open(pdf_path)
    
    # Cache shape XObjects
    spdf = os.path.join(global_stamps_dir, f"{base_shape}.pdf")
    shape_xobj_xref = None
    
    src = fitz.open(spdf)
    doc.insert_pdf(src)
    src.close()
    tmp = doc[-1]
    
    # Extract AP from Stamp
    for ca in tmp.annots() or []:
        if ca.type[1] == "Stamp":
            ap = doc.xref_get_key(ca.xref, "AP")
            if ap[0] == "dict":
                nm = re.search(r'/N\s+(\d+)\s+0\s+R', ap[1])
                shape_xobj_xref = int(nm.group(1)) if nm else ca.xref
                break
                
    if not shape_xobj_xref:
        # Fall back to whole page
        res2 = doc.xref_get_key(tmp.xref, "Resources")
        tmp.clean_contents()
        cl = tmp.get_contents()
        if cl:
            cs = doc.xref_stream(cl[0])
            b = tmp.rect
            shape_xobj_xref = doc.get_new_xref()
            od = f"<< /Type /XObject /Subtype /Form /BBox [{b.x0} {b.y0} {b.x1} {b.y1}] /Matrix [1 0 0 1 0 0] "
            if res2[0] == "dict":
                od += f"/Resources {res2[1]} "
            od += ">>"
            doc.update_object(shape_xobj_xref, od)
            doc.update_stream(shape_xobj_xref, cs)
    
    doc.delete_page(-1)
    
    if not shape_xobj_xref:
        print("Failed to extract shape")
        return
        
    print(f"Shape XObject XREF: {shape_xobj_xref}")
    
    # Now build composite
    page = doc[0] # first page
    annot = None
    for a in page.annots():
        if a.type[1] == "Stamp":
            annot = a
            break
            
    if not annot:
        print("No stamp annot found on page 0")
        return
        
    ann_rect = annot.rect
    rw, rh = ann_rect.width, ann_rect.height
    fs = max(min(rw, rh) * 0.5, 6.0)
    
    bbox_raw = doc.xref_get_key(shape_xobj_xref, "BBox")
    sx = sy = 1.0
    ex, ey = 0.0, 0.0
    if bbox_raw[0] != "null":
        try:
            bvals = list(map(float, bbox_raw[1].strip("[]").split()))
            sw, sh = bvals[2] - bvals[0], bvals[3] - bvals[1]
            sx = rw / sw if sw else 1.0
            sy = rh / sh if sh else 1.0
            ex = -bvals[0] * sx
            ey = -bvals[1] * sy
        except Exception as e:
            print("Error parsing bbox", e)
            
    tx = rw / 2
    ty = (rh - fs) / 2
    
    stream = (
        f"q\n{sx:g} 0 0 {sy:g} {ex:g} {ey:g} cm\n/ShapeForm Do\nQ\n"
        f"BT\n/Helv {fs:g} Tf\n1 0 0 rg\n"
        f"{tx:g} {ty:g} Td\n(42) Tj\nET\n"
    ).encode("latin1")
    
    res_dict = (
        f"<< /XObject << /ShapeForm {shape_xobj_xref} 0 R >>"
        f" /Font << /Helv << /Type /Font /Subtype /Type1"
        f" /BaseFont /Helvetica >> >> >>"
    )
    comp_xref = doc.get_new_xref()
    bbox_str = f"[0 0 {rw} {rh}]"
    comp_dict = f"<< /Type /XObject /Subtype /Form /BBox {bbox_str} /Matrix [1 0 0 1 0 0] /Resources {res_dict} >>"
    
    doc.update_object(comp_xref, comp_dict)
    doc.update_stream(comp_xref, stream)
    
    doc.xref_set_key(annot.xref, "AS", "null")
    doc.xref_set_key(annot.xref, "AP", f"<< /N {comp_xref} 0 R >>")
    doc.xref_set_key(annot.xref, "Subtype", "/Stamp")
    
    doc.save("test_composite.pdf")
    print("Saved test_composite.pdf")

if __name__ == "__main__":
    global_stamps_dir = "c:/pinchus/web_viewer/data/global_stamps"
    test_composite("c:/pinchus/Projects/Test/pdfs/15 Getzel 05-26-2026_1.pdf", None, "User", global_stamps_dir)
