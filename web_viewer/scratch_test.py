import fitz
import os

def test_page_contents_to_ap():
    # Create src doc with drawings and text
    src = fitz.open()
    p = src.new_page(width=100, height=100)
    p.draw_circle(fitz.Point(50, 50), 40, color=(1,0,0), fill=(1,1,0))
    p.insert_text(fitz.Point(20, 50), "STAMP", color=(0,0,1))
    src.save("src.pdf")
    src.close()

    # Create target doc
    dst = fitz.open()
    p2 = dst.new_page(width=500, height=500)
    target_annot = p2.add_rect_annot(fitz.Rect(100, 100, 300, 300))
    target_annot.set_colors(stroke=(0, 1, 0))
    target_annot.update()
    
    src = fitz.open("src.pdf")
    
    # 1. Insert src into dst
    dst.insert_pdf(src)
    temp_page = dst[-1]
    
    # 2. Get Resources and Contents of the temp_page
    page_xref = temp_page.xref
    res_val = dst.xref_get_key(page_xref, "Resources")
    
    # Combine all contents into one stream
    temp_page.clean_contents()
    contents_list = temp_page.get_contents()
    if not contents_list:
        print("Page has no contents")
        return
        
    contents_xref = contents_list[0]
    contents_stream = dst.xref_stream(contents_xref)
    
    # 3. Create a NEW XObject stream in dst
    new_xobj_xref = dst.get_new_xref()
    bbox = temp_page.rect
    bbox_str = f"[{bbox.x0} {bbox.y0} {bbox.x1} {bbox.y1}]"
    
    # Build XObject dictionary string
    xobj_dict = f"<< /Type /XObject /Subtype /Form /BBox {bbox_str} /Matrix [1 0 0 1 0 0] "
    if res_val[0] == "dict":
        xobj_dict += f"/Resources {res_val[1]} "
    xobj_dict += ">>"
    
    dst.update_object(new_xobj_xref, xobj_dict)
    dst.update_stream(new_xobj_xref, contents_stream)
        
    # 4. Set AP of target_annot to this new XObject
    ap_str = f"<< /N {new_xobj_xref} 0 R >>"
    dst.xref_set_key(target_annot.xref, "AS", "null")
    dst.xref_set_key(target_annot.xref, "AP", ap_str)
    
    # 5. Delete temp page
    dst.delete_page(-1)
    
    dst.save("dst.pdf")
    print("Success")

test_page_contents_to_ap()
