import os
import fitz
import re

def test_xobj(pdf_path, xref, base_shape, global_stamps_dir):
    doc = fitz.open(pdf_path)
    
    # 1. Open shape PDF and find stamp rect
    spdf = os.path.join(global_stamps_dir, f"{base_shape}.pdf")
    shape_doc = fitz.open(spdf)
    
    src_page_idx = 0
    src_rect = None
    for i in range(len(shape_doc)):
        for a in shape_doc[i].annots() or []:
            if a.type[1] == "Stamp":
                src_page_idx = i
                src_rect = a.rect
                break
        if src_rect:
            break
            
    if not src_rect:
        print("No stamp found in shape PDF")
        return
        
    print(f"Found shape stamp on page {src_page_idx} at {src_rect}")

    # 2. Get target annotation
    page = doc[1]
    annot = None
    for a in page.annots():
        if a.type[1] == "Stamp":
            annot = a
            break
            
    if not annot:
        print("No stamp annot found in target PDF")
        return
        
    ann_rect = annot.rect
    rw, rh = ann_rect.width, ann_rect.height
    fs = max(min(rw, rh) * 0.5, 6.0)
    
    print(f"Target annot: {ann_rect} (rw={rw}, rh={rh})")
    
    # 3. Create temporary page sized to the annotation
    tmp_page = doc.new_page(-1, width=rw, height=rh)
    
    # 4. Draw the shape perfectly scaled using show_pdf_page
    tmp_page.show_pdf_page(tmp_page.rect, shape_doc, src_page_idx, clip=src_rect)
    
    # 5. Draw the text perfectly centered
    text_rect = fitz.Rect(0, 0, rw, rh)
    tmp_page.insert_textbox(
        text_rect,
        "42",
        fontsize=fs,
        fontname="helv",
        color=(1, 0, 0),
        align=fitz.TEXT_ALIGN_CENTER
    )
    
    # 6. Extract the whole page into a Form XObject
    res2 = doc.xref_get_key(tmp_page.xref, "Resources")
    tmp_page.clean_contents()
    cl = tmp_page.get_contents()
    
    if not cl:
        print("Failed to get contents")
        return
        
    cs = doc.xref_stream(cl[0])
    b = tmp_page.rect
    comp_xref = doc.get_new_xref()
    od = f"<< /Type /XObject /Subtype /Form /BBox [{b.x0} {b.y0} {b.x1} {b.y1}] /Matrix [1 0 0 1 0 0] "
    if res2[0] in ("dict", "xref"):
        od += f"/Resources {res2[1]} "
    od += ">>"
    
    doc.update_object(comp_xref, od)
    doc.update_stream(comp_xref, cs)
    
    # 7. Delete temporary page
    doc.delete_page(-1)
    
    # 8. Set as AP
    doc.xref_set_key(annot.xref, "AS", "null")
    doc.xref_set_key(annot.xref, "AP", f"<< /N {comp_xref} 0 R >>")
    doc.xref_set_key(annot.xref, "Subtype", "/Stamp")
    
    doc.save("test_xobj_output.pdf")
    print(f"Saved test_xobj_output.pdf with comp_xref {comp_xref}")

if __name__ == "__main__":
    global_stamps_dir = "c:/pinchus/web_viewer/data/global_stamps"
    test_xobj("c:/pinchus/Projects/Test/pdfs/15 Getzel 05-26-2026_1 2.pdf", None, "User", global_stamps_dir)
