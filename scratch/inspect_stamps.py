import fitz
import sys

def inspect_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    stamps_found = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        annots = page.annots()
        if annots:
            for annot in annots:
                info = annot.info
                # Type 13 is STAMP
                if annot.type[0] == 13:
                    stamps_found.append({
                        "page": page_num + 1,
                        "type": annot.type[1],
                        "info": info,
                        "rect": annot.rect
                    })
                else:
                    # Also collect other annotations just in case
                    stamps_found.append({
                        "page": page_num + 1,
                        "type": annot.type[1],
                        "info": info,
                        "rect": annot.rect,
                        "custom_type": annot.type[0]
                    })

    if not stamps_found:
        print("No annotations found.")
    else:
        print(f"Found {len(stamps_found)} annotations:")
        for s in stamps_found:
            print(f"Page {s['page']}: {s['type']} (Subject: {s['info'].get('subject', 'N/A')}, Content: {s['info'].get('content', 'N/A')}) at {s['rect']}")

    # Also check for Form XObjects that might be stamps
    # This is more complex, but we can look for objects with "Stamp" in their name or metadata
    
    doc.close()

if __name__ == "__main__":
    pdf_path = r"c:\pinchus\Sample pdfs\Drrwaings samples\DOC-20250715-WA0309..pdf"
    inspect_pdf(pdf_path)
