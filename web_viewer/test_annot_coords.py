import fitz
import sys

doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]

# Add an annotation in visual space (100, 100) -> (200, 200)
# And one in unrotated space
vis_rect = fitz.Rect(100, 100, 200, 200)
unrot_rect = vis_rect * ~page.rotation_matrix

print("Visual rect:", vis_rect)
print("Unrotated rect:", unrot_rect)

# We want to see where they appear visually.
annot1 = page.add_freetext_annot(vis_rect, "VisualSpace", fontsize=10, fill_color=(1,0,0))
annot2 = page.add_freetext_annot(unrot_rect, "UnrotatedSpace", fontsize=10, fill_color=(0,1,0))

# Try setting Rect manually
annot3 = page.add_freetext_annot(fitz.Rect(0,0,10,10), "ManualSet", fontsize=10, fill_color=(0,0,1))
annot3_vis_rect = fitz.Rect(300, 100, 400, 200)
annot3_unrot_rect = annot3_vis_rect * ~page.rotation_matrix
doc.xref_set_key(annot3.xref, "Rect", f"[{annot3_unrot_rect.x0} {annot3_unrot_rect.y0} {annot3_unrot_rect.x1} {annot3_unrot_rect.y1}]")

doc.save(r"C:\pinchus\web_viewer\test_annot.pdf")
print("Saved to test_annot.pdf")
