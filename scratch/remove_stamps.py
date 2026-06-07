import fitz
import os

def remove_all_annots(pdf_path, output_path):
    doc = fitz.open(pdf_path)
    total_removed = 0
    
    for page in doc:
        annots = list(page.annots())
        for annot in annots:
            page.delete_annot(annot)
            total_removed += 1
            
    doc.save(output_path)
    doc.close()
    return total_removed

if __name__ == "__main__":
    input_pdf = r"c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309..pdf"
    output_pdf = r"c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309_no_stamps.pdf"
    
    removed_count = remove_all_annots(input_pdf, output_pdf)
    print(f"Removed {removed_count} annotations.")
    print(f"Saved to: {output_pdf}")
