import fitz
import os
import sys

pdf_dir = r'c:\pinchus\Sample pdfs\Drrwaings samples'
pdfs = [f for f in os.listdir(pdf_dir) if f.endswith('.pdf')]

sys.path.append(r'c:\pinchus\Scripts')
import detect_subject_items

for pdf_file in pdfs:
    doc = fitz.open(os.path.join(pdf_dir, pdf_file))
    for page in doc:
        for annot in page.annots() or []:
            if annot.info.get('subject') == 'grill 6':
                print(f'Found grill 6 in {pdf_file} page {page.number}')
                pending = detect_subject_items.get_stamp_appearance_xrefs(doc, annot.xref)
                seen = set()
                while pending:
                    xref = pending.pop(0)
                    if xref in seen: continue
                    seen.add(xref)
                    stream = doc.xref_stream(xref)
                    if stream:
                        text = stream.decode('latin1', errors='ignore')
                        print('--- STREAM START ---')
                        print(text)
                        print('--- STREAM END ---')
                        
                    for child_xref in detect_subject_items.get_form_xobject_xrefs(doc, xref):
                        if child_xref not in seen:
                            pending.append(child_xref)
