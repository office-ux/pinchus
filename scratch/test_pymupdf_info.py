import fitz
import sys

def main(pdf_path):
    doc = fitz.open(pdf_path)
    for page in doc:
        for annot in page.annots():
            if annot.type[1] == "Stamp":
                print(annot.info)
                print(doc.xref_get_key(annot.xref, "NM"))
                print(doc.xref_get_key(annot.xref, "Name"))
                print(doc.xref_get_key(annot.xref, "StampID"))
                return
    print("No stamps found")

if __name__ == "__main__":
    main(sys.argv[1])
