import sys, fitz
sys.path.append(r'c:\pinchus\working_testing_scripts')
import detect_boxes, detect_subject_items, detect_matching_lines
cfg = detect_subject_items.load_config()
pdf = r'c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309_no_stamps.pdf'
m, _ = detect_subject_items.scan_pdf(pdf, cfg['targets'])
sigs = detect_boxes.get_unique_signatures_exploded(m)
print("Signature 0 segments:")
if sigs:
    for s in sigs[0]['segments']:
        print(f"  Length: {s['length']:.2f}, Weight: {s['line_weight']:.2f}, Color: {s['stroke_color']}")

doc = fitz.open(pdf)
page = doc[0]
items = list(detect_boxes.iter_page_items_exploded(page))
print(f"Page 1 has {len(items)} items")

if sigs and sigs[0]['segments']:
    target_len = sigs[0]['segments'][0]['length']
    close_items = [i for i in items if abs(i['length'] - target_len) < 1.0]
    print(f"Found {len(close_items)} items on page 1 with length close to {target_len:.2f}")
    for i in close_items[:5]:
        print(f"  Length: {i['length']:.2f}, Weight: {i['line_weight']:.2f}, Color: {i['stroke_color']}")
