import fitz
import os

def explore_annots(pdf_path):
    print(f"Exploring annotations in {pdf_path}...")
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        for annot in page.annots():
            info = annot.info
            print(f"Page {page_num+1} | Type: {annot.type[1]} | Subject: {info.get('subject')} | Title: {info.get('title')}")

if __name__ == "__main__":
    folder = r"c:\pinchus\Sample pdfs\Drrwaings samples"
    for f in os.listdir(folder):
        if f.endswith(".pdf"):
            explore_annots(os.path.join(folder, f))
