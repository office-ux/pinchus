import fitz

def duplicate_stamp_api(doc, page_num, src_xref, new_name, new_uuid, center_x, center_y, pdf_path):
    page = doc[page_num - 1]
    src_annot = None
    for a in page.annots():
        if a.xref == src_xref:
            src_annot = a
            break
            
    if not src_annot:
        raise ValueError("Source stamp not found")
        
    w = src_annot.rect.width
    h = src_annot.rect.height
    new_rect = fitz.Rect(center_x - w/2, center_y - h/2, center_x + w/2, center_y + h/2)
    
    # Extract number from new_name (e.g. hex_33 -> 33)
    parts = new_name.rsplit('_', 1)
    num_text = parts[1] if len(parts) > 1 else "1"
    
    fixed_fs = max(min(new_rect.width, new_rect.height) * 0.5, 6.0)
    
    label_color = [1.0, 0.0, 0.0]
    new_annot = page.add_freetext_annot(
        new_rect,
        num_text,
        fontsize=fixed_fs,
        fontname="helv",
        text_color=label_color,
        fill_color=(1.0, 1.0, 1.0),
        align=fitz.TEXT_ALIGN_CENTER,
    )
    new_annot.set_border(width=2.0)
    
    stamp_subject = src_annot.info.get("subject", "system")
    new_annot.set_info(subject=stamp_subject, title="")
    new_annot.update()
    
    import urllib.parse
    encoded_pdf = urllib.parse.quote(pdf_path.replace("\\", "/"))
    base_url = "https://tabsoftwear.salcerandco.com/"
    link = {
        "kind": fitz.LINK_URI,
        "from": new_rect,
        "uri": f"{base_url}?pdf={encoded_pdf}#stamp-{new_uuid}"
    }
    page.insert_link(link)
    
    doc.xref_set_key(new_annot.xref, "Subtype", "/Stamp")
    doc.xref_set_key(new_annot.xref, "NM", f"({new_name})")
    doc.xref_set_key(new_annot.xref, "Name", f"/{new_uuid}")
    doc.xref_set_key(new_annot.xref, "StampID", f"({new_uuid})")
    
    return new_annot.xref
