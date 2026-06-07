import fitz

def check_layers(pdf_path):
    doc = fitz.open(pdf_path)
    ocgs = doc.get_ocgs()
    if ocgs:
        print("Optional Content Groups (Layers):")
        for xref, info in ocgs.items():
            print(f"XREF {xref}: {info}")
    else:
        print("No OCGs found.")
    doc.close()

if __name__ == "__main__":
    pdf_path = r"c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309..pdf"
    check_layers(pdf_path)
