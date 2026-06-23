import sys
sys.path.insert(0, 'c:/pinchus')
import detect_subject_items as si

pdf_path = r'c:/pinchus/Projects/asdfav/pdfs/15 Getzel 05-26-2026_1 2.pdf'
matches, path = si.load_pdf_pattern_matches(pdf_path)
print("Patterns path:", path)
print("Matches count:", len(matches))
for m in matches:
    segs = m["segments"]
    lengths = m["lengths"]
    print("  target=%s type=%s page=%s line_count=%s seg_count=%s" % (
        m["target"], m["type"], m["page"], m["line_count"], len(segs)))
    print("  lengths:", [round(l, 2) for l in lengths[:6]])
    for seg in segs[:3]:
        print("    seg shape_type=%s start=%s end=%s" % (
            seg.get("shape_type"), seg.get("start"), seg.get("end")))
