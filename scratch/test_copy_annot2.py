import fitz
import sys

def main(pdf_path, source_xref, dx=50, dy=50):
    doc = fitz.open(pdf_path)
    src_page = None
    src_annot = None
    for p in doc:
        for a in p.annots():
            if a.xref == source_xref:
                src_page = p
                src_annot = a
                break
        if src_page:
            break
            
    if not src_page:
        print("Annot not found")
        return
        
    print(f"Annot colors: {src_annot.colors}")
    print(f"Annot border: {src_annot.border}")
    print(f"Annot info: {src_annot.info}")
    
    # We can create a new annot with these properties!
    new_rect = src_annot.rect + fitz.Point(dx, dy)
    new_annot = src_page.add_freetext_annot(
        new_rect,
        "33",
        fontsize=max(min(new_rect.width, new_rect.height) * 0.5, 6.0),
        fontname="helv",
        text_color=src_annot.colors.get("stroke", (1,0,0)),
        fill_color=(1,1,1),
        align=fitz.TEXT_ALIGN_CENTER
    )
    new_annot.set_border(width=2.0)
    new_annot.set_colors(stroke=src_annot.colors.get("stroke", (1,0,0)))
    new_annot.set_info(subject=src_annot.info.get("subject", ""), title="")
    new_annot.update()
    
    doc.xref_set_key(new_annot.xref, "Subtype", "/Stamp")
    doc.xref_set_key(new_annot.xref, "NM", f"(hex_33)")
    doc.xref_set_key(new_annot.xref, "Name", f"/(new-uuid-123)")
    doc.xref_set_key(new_annot.xref, "StampID", f"(new-uuid-123)")
    
    print(f"Created new annot: {new_annot.xref}")

if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
