import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import detect_patterns
import detect_patterns_output
import detect_subject_items
import fitz

def test():
    pdf_path = r"c:\pinchus\Projects\Test\pdfs\32 Center hill road ASBUILT.pdf"
    cfg = detect_subject_items.load_config()
    
    # Check what matches are loaded
    matches, path = detect_subject_items.load_pdf_pattern_matches(pdf_path)
    
    patterns = detect_patterns.detect_patterns_parallel(pdf_path, cfg)
    output_path = detect_patterns_output.save_pattern_pdf(pdf_path, patterns, cfg, overwrite_input=False)
    
    doc = fitz.open(output_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        for annot in page.annots() or []:
            xref = annot.xref
            subj = annot.info.get("subject")
            print(f"Annotation xref={xref}")
            print(f"  Raw object: {doc.xref_object(xref)}")
            print(f"  Subject info: {subj}")
    doc.close()

if __name__ == "__main__":
    test()
