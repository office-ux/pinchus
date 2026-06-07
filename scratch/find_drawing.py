import fitz
import os
import math

folder = 'Sample pdfs/Drrwaings samples'
for file in os.listdir(folder):
    if file.lower().endswith('.pdf'):
        path = os.path.join(folder, file)
        try:
            doc = fitz.open(path)
            for i, page in enumerate(doc):
                drawings = page.get_drawings()
                for d_idx, d in enumerate(drawings):
                    for i_idx, item in enumerate(d.get('items', [])):
                        if item[0] == 'c':
                            p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                            # Let's check points coordinates or approx length
                            d1 = math.hypot(p2.x - p1.x, p2.y - p1.y)
                            d2 = math.hypot(p3.x - p2.x, p3.y - p2.y)
                            d3 = math.hypot(p4.x - p3.x, p4.y - p3.y)
                            length = d1 + d2 + d3
                            if abs(length - 140.86) < 1.0 or abs(p1.x - 1343.9) < 20 or abs(p1.y - 505.7) < 20:
                                print(f'{file} page {i+1} matched drawing {d_idx}_{i_idx}: p1={p1}, p4={p4}, length={length:.2f}')
        except Exception as e:
            print(f'Error reading {file}: {e}')
