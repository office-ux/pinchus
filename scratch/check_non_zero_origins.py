import fitz
import os

folder = 'Sample pdfs/Drrwaings samples'
for file in os.listdir(folder):
    if file.lower().endswith('.pdf'):
        path = os.path.join(folder, file)
        try:
            doc = fitz.open(path)
            for i, page in enumerate(doc):
                cb = page.cropbox
                mb = page.mediabox
                if cb.x0 != 0 or cb.y0 != 0 or mb.x0 != 0 or mb.y0 != 0:
                    print(f'{file} Page {i+1}: cropbox={cb}, mediabox={mb}')
            doc.close()
        except Exception as e:
            print(f'Error reading {file}: {e}')
