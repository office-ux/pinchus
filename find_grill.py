import os
import fitz

def explore(root):
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith('.pdf'):
                path = os.path.join(dirpath, f)
                try:
                    doc = fitz.open(path)
                    for i, page in enumerate(doc):
                        for annot in page.annots():
                            subject = (annot.info.get('subject') or '').lower()
                            if 'grill' in subject:
                                print(f"FOUND in {path} Page {i+1}: Subject='{annot.info.get('subject')}' Type={annot.type[1]} Rect={annot.rect}")
                except Exception as e:
                    pass

if __name__ == "__main__":
    explore(r"c:\pinchus\Sample pdfs")
