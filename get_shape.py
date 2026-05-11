import os
from detect_pencil import detect_elements, select_pdf_from_folder

def get_shapes(pdf_path, target_subjects):
    """
    Finds elements with the given target subjects and returns their shapes (vertices).
    """
    print(f"Detecting shapes in {pdf_path}...")
    elements = detect_elements(pdf_path, target_subjects)
    
    shapes = []
    if elements:
        for i, el in enumerate(elements):
            vertices = el.get("vertices")
            
            # Format the shape data
            shape_data = {
                "id": el.get("id") or f"element_{i}",
                "type": el.get("type"),
                "subject": el.get("subject"),
                "page": el.get("page")
            }
            
            if vertices:
                shape_data["vertices"] = vertices
            else:
                # Fallback to rect if no vertices (e.g. for simple rectangles)
                shape_data["rect"] = el.get("rect")
                
            shapes.append(shape_data)
                
    return shapes

if __name__ == "__main__":
    folder_path = r"c:\pinchus\Sample pdfs\Drrwaings samples"
    pdf_file = select_pdf_from_folder(folder_path)
    
    if pdf_file:
        targets = ["Pencill", "HVAC return", "HVAC Supply"]
        shapes = get_shapes(pdf_file, targets)
    
    if shapes:
        print(f"\n--- Found {len(shapes)} Shapes ---")
        for idx, shape in enumerate(shapes, 1):
            print(f"Shape {idx} (Page {shape['page']}):")
            print(f"  Type: {shape['type']}")
            print(f"  Subject: {shape['subject']}")
            
            if "vertices" in shape:
                vertices = shape["vertices"]
                print(f"  Vertices type: {type(vertices)}")
                # If it's a list of lists (like for Ink)
                if vertices and isinstance(vertices, list) and isinstance(vertices[0], list):
                    print(f"  Strokes count: {len(vertices)}")
                    print(f"  First stroke, first few points: {vertices[0][:3]} ...")
                # If it's a flat list (like for Polygon)
                elif vertices and isinstance(vertices, list):
                    print(f"  Points count: {len(vertices)}")
                    print(f"  First few points: {vertices[:3]} ...")
                else:
                    print(f"  Vertices: {vertices}")
            else:
                print(f"  Rect: {shape.get('rect')} (No vertices found)")
    else:
        print("\nNo shapes found.")
