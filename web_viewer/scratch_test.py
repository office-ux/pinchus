import fitz
import os

def test_copy_annot():
    # Create src doc with a stamp annot
    src = fitz.open()
    p = src.new_page()
    annot = p.add_rect_annot(fitz.Rect(0, 0, 100, 100))
    annot.set_colors(stroke=(1, 0, 0))
    annot.update()
    src.save("src.pdf")
    src.close()

    # Create target doc with a different annot
    dst = fitz.open()
    p2 = dst.new_page()
    target_annot = p2.add_rect_annot(fitz.Rect(50, 50, 200, 200))
    target_annot.set_colors(stroke=(0, 0, 1))
    target_annot.update()
    
    print("Target AP before:", dst.xref_get_key(target_annot.xref, "AP"))
    
    # 1. Open src and insert its page into dst
    src = fitz.open("src.pdf")
    dst.insert_pdf(src)
    
    # 2. Get the copied annot on the new page
    temp_page = dst[-1]
    copied_annot = temp_page.first_annot
    print("Copied AP:", dst.xref_get_key(copied_annot.xref, "AP"))
    
    # 3. Copy AP dictionary string
    ap_val = dst.xref_get_key(copied_annot.xref, "AP")[1]
    
    # 4. Set target AP
    dst.xref_set_key(target_annot.xref, "AP", ap_val)
    print("Target AP after:", dst.xref_get_key(target_annot.xref, "AP"))
    
    # 5. Delete temp page
    dst.delete_page(-1)
    
    dst.save("dst.pdf")
    print("Success")

test_copy_annot()
