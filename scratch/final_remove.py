import fitz
import os
import shutil

def remove_stamps_and_save(pdf_path):
    # Create a backup
    backup_path = pdf_path + ".bak"
    shutil.copy2(pdf_path, backup_path)
    print(f"Created backup at {backup_path}")
    
    doc = fitz.open(pdf_path)
    total_removed = 0
    
    for page in doc:
        annots = list(page.annots())
        for annot in annots:
            page.delete_annot(annot)
            total_removed += 1
            
    # Save to a temporary file first to avoid corruption
    temp_path = pdf_path + ".tmp"
    doc.save(temp_path, garbage=4, deflate=True)
    doc.close()
    
    # Replace original with cleaned version
    os.remove(pdf_path)
    os.rename(temp_path, pdf_path)
    
    return total_removed

if __name__ == "__main__":
    pdf_path = r"c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309..pdf"
    count = remove_stamps_and_save(pdf_path)
    print(f"Successfully removed {count} stamps from {pdf_path}")
