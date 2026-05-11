import fitz  # PyMuPDF
import os

def select_pdf_from_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"Folder not found: {folder_path}")
        return None
        
    pdfs = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not pdfs:
        print(f"No PDF files found in {folder_path}")
        return None
        
    print(f"\nPDF files found in {folder_path}:")
    for i, pdf in enumerate(pdfs, 1):
        print(f"{i}. {pdf}")
        
    while True:
        choice = input(f"\nEnter the number of the file to scan (1-{len(pdfs)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(pdfs):
                return os.path.join(folder_path, pdfs[idx])
        print("Invalid selection. Please try again.")

def detect_elements(pdf_path, target_subjects):
    print(f"Opening {pdf_path}...")
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Failed to open PDF: {e}")
        return

    found_elements = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Iterate over all annotations on the page
        annot = page.first_annot
        while annot:
            # Info is a dictionary containing annotation metadata like subject, title, etc.
            info = annot.info
            subject = info.get("subject", "")
            
            # Check if subject matches any of our target subjects (case-insensitive)
            if subject and any(ts.lower() in subject.lower() for ts in target_subjects):
                found_elements.append({
                    "page": page_num + 1,
                    "type": annot.type[1], # String description of the type
                    "subject": subject,
                    "content": info.get("content", ""),
                    "rect": [round(c, 2) for c in annot.rect],
                    "author": info.get("title", ""), # 'title' often maps to the Author property
                    "name": info.get("name", ""),
                    "id": info.get("id", ""),
                    "creationDate": info.get("creationDate", ""),
                    "modDate": info.get("modDate", ""),
                    "colors": annot.colors if hasattr(annot, 'colors') else None,
                    "opacity": annot.opacity if hasattr(annot, 'opacity') else None,
                    "vertices": annot.vertices if hasattr(annot, 'vertices') else None,
                    "full_info": info # Store the full info dict for debugging
                })
            
            annot = annot.next

    if not found_elements:
        print(f"No elements with subjects {target_subjects} found.")
        return []
    else:
        print(f"Found {len(found_elements)} elements with subjects {target_subjects}:")
        for idx, el in enumerate(found_elements, 1):
            print(f"{idx}. Page: {el['page']} | Type: {el['type']} | Subject: '{el['subject']}' | Content: '{el['content']}' | Rect: {el['rect']}")
            print(f"   Author: {el['author']} | Name/ID: {el['id']} (Name prop: {el['name']}) | Created: {el['creationDate']} | Modified: {el['modDate']}")
            print(f"   Colors: {el['colors']} | Opacity: {el['opacity']}")
            print(f"   Full info dict: {el['full_info']}")

    return found_elements

if __name__ == "__main__":
    folder_path = r"c:\pinchus\Sample pdfs\Drrwaings samples"
    pdf_file = select_pdf_from_folder(folder_path)
    
    if pdf_file:
        targets = ["HVAC return", "HVAC Supply"]
        detect_elements(pdf_file, targets)
