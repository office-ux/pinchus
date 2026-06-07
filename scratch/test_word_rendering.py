import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'web_viewer'))

import doc_renderer

def test_render():
    template_path = r"c:\pinchus\report word samples\FCU Report.docx"
    output_path = r"c:\pinchus\scratch\FCU_Report_populated.docx"
    
    stamps_data = [
        {
            "fields": [
                {"name": "DWG #", "value": "M-101"},
                {"name": "#", "value": "1"},
                {"name": "TYPE", "value": "CD"},
                {"name": "SIZE", "value": "12x12"},
                {"name": "K-factor", "value": "1.02"},
                {"name": "DESIGN CFM", "value": "150"},
                {"name": "PRELIMINARY VEL", "value": "-"},
                {"name": "PRELIMINARY CFM", "value": "-"},
                {"name": "PRELIMINARY %", "value": "-"},
                {"name": "FINAL VEL", "value": "400"},
                {"name": "FINAL CFM", "value": "145"},
                {"name": "FINAL %", "value": "97%"}
            ]
        },
        {
            "fields": [
                {"name": "DWG #", "value": "M-101"},
                {"name": "#", "value": "2"},
                {"name": "TYPE", "value": "CD"},
                {"name": "SIZE", "value": "12x12"},
                {"name": "K-factor", "value": "1.02"},
                {"name": "DESIGN CFM", "value": "120"},
                {"name": "PRELIMINARY VEL", "value": "-"},
                {"name": "PRELIMINARY CFM", "value": "-"},
                {"name": "PRELIMINARY %", "value": "-"},
                {"name": "FINAL VEL", "value": "380"},
                {"name": "FINAL CFM", "value": "118"},
                {"name": "FINAL %", "value": "98%"}
            ]
        }
    ]
    
    print("Populating template...")
    doc_renderer.populate_docx_template(template_path, output_path, stamps_data)
    print(f"Template populated successfully! Output saved to: {output_path}")

if __name__ == "__main__":
    test_render()
