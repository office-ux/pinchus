import os
import json
import fitz

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config.json: {e}")
    return {}

def detect_stamps_on_pdf(pdf_path, cfg=None):
    if not cfg:
        cfg = load_config()
        
    doc = fitz.open(pdf_path)
    total_stamps = 0
    
    # We will highlight stamps with a distinct orange/gold border and a translucent fill
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_stamps = 0
        
        for annot in page.annots() or []:
            if annot.type[1] == "Stamp":
                rect = annot.rect
                subject = annot.info.get("subject") or "Stamp"
                title = annot.info.get("title") or "User"
                
                # Draw a highlight rectangle around it (orange border + translucent orange fill)
                shape = page.new_shape()
                shape.draw_rect(rect)
                shape.finish(color=(1.0, 0.5, 0.0), fill=(1.0, 0.8, 0.5), width=2, fill_opacity=0.3)
                shape.commit()
                
                # Add a text label above the stamp
                label = f"{subject} ({title})"
                fs = 9
                tw = fitz.get_text_length(label, fontsize=fs)
                text_rect = fitz.Rect(rect.x0, rect.y0 - fs - 4, rect.x0 + tw + 6, rect.y0 - 1)
                
                # Draw background for the label
                shape = page.new_shape()
                shape.draw_rect(text_rect)
                shape.finish(color=(1.0, 0.5, 0.0), fill=(1.0, 0.9, 0.7), width=1, fill_opacity=0.9)
                shape.commit()
                
                # Insert label text
                page.insert_text((rect.x0 + 3, rect.y0 - 4), label, fontsize=fs, color=(0, 0, 0))
                
                page_stamps += 1
                total_stamps += 1
                
        if page_stamps > 0:
            print(f"Page {page_num+1}: Found and highlighted {page_stamps} stamps.")
            
    if total_stamps > 0:
        # Extract project name from pdf_path
        project_name = "test"
        normalized = os.path.normpath(pdf_path)
        parts = normalized.split(os.sep)
        for i, part in enumerate(parts):
            if part.lower() == "projects" and i + 1 < len(parts):
                project_name = parts[i + 1]
                break
                
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(base_dir).lower() == "web_viewer":
            base_dir = os.path.dirname(base_dir)
            
        projects_output_dir = os.path.normpath(os.path.join(base_dir, "Projects", project_name, "output"))
        os.makedirs(projects_output_dir, exist_ok=True)
        
        base_name = os.path.basename(pdf_path).replace(".pdf", "_stamps_detected.pdf")
        output_path = os.path.join(projects_output_dir, base_name)
        
        doc.save(output_path)
        doc.close()
        print(f"Stamp detection completed! Highlighted {total_stamps} stamps.")
        print(f"Saved to: {output_path}")
        return output_path
    else:
        doc.close()
        print("No stamps found on the drawing.")
        return None

def main():
    cfg = load_config()
    if not cfg:
        return
    folder_path = cfg.get("paths", {}).get("input_folder")
    if not folder_path or not os.path.exists(folder_path):
        print(f"Input folder path not found or invalid: {folder_path}")
        return
        
    import detect_subject_items as subject_items
    pdf_path = subject_items.select_pdf(folder_path)
    if not pdf_path:
        return
    
    detect_stamps_on_pdf(pdf_path, cfg)

if __name__ == "__main__":
    main()
