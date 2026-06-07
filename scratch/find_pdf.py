import fitz
import os

folder = 'Sample pdfs/Drrwaings samples'
for file in os.listdir(folder):
    if file.lower().endswith('.pdf'):
        path = os.path.join(folder, file)
        try:
            doc = fitz.open(path)
            for i, page in enumerate(doc):
                text = page.get_text()
                if 'BA' in text and ('56' in text or '9' in text):
                    print(f'{file} page {i+1} matches text: {repr(text[:200])}')
        except Exception as e:
            print(f'Error reading {file}: {e}')
