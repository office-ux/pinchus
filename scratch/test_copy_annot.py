import fitz
import sys

def main(pdf_path, source_xref, dx=50, dy=50):
    doc = fitz.open(pdf_path)
    
    # find the page of the annot
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
        
    # How to copy?
    # We can read all keys and write them to a new annot? No, PyMuPDF can't easily create raw annots unless we use xref magic.
    # What if we just use src_annot.rect?
    print(f"Source annot: {src_annot.type}, rect: {src_annot.rect}")
    
if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
