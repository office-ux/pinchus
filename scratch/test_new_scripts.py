import sys
import os
import fitz

# Ensure the workspace root folder is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import detect_subject_items as subject_items
import detect_matching_lines as matching_lines
import detect_patterns as detect_patterns
import detect_patterns_output as detect_patterns_output

if __name__ == '__main__':
    # Load config
    cfg = subject_items.load_config()
    pdf_path = os.path.join(cfg["paths"]["input_folder"], "mechanical2.pdf")

    print("PDF Path:", pdf_path)
    print("Config Targets:", cfg["targets"])

    # Step 1: scan_pdf
    print("\n--- Running scan_pdf ---")
    test_targets = ['grill', 'grill 1', 'grill 4', 'grill 6']
    matches, summary = subject_items.scan_pdf(pdf_path, test_targets)
    print(f"Found {len(matches)} matched annotations.")

    # Step 2: detect_patterns
    print("\n--- Running detect_patterns ---")
    test_cfg = cfg.copy()
    test_cfg["targets"] = test_targets
    patterns = detect_patterns.detect_patterns_parallel(pdf_path, test_cfg)
    print(f"Detected {len(patterns)} patterns.")

    # Save output PDF
    if patterns:
        detect_patterns_output.save_pattern_pdf(pdf_path, patterns, test_cfg)

    # Verify that output file is generated and contains the "Vector PDF Inspector" OCG layer
    if patterns:
        out_dir = cfg["paths"]["output_folder"]
        out_files = [f for f in os.listdir(out_dir) if "mechanical2_patterns_detected" in f and f.endswith(".pdf")]
        print("\nGenerated output files in folder:", out_files)
        
        # Check the newest output file
        out_files_paths = [os.path.join(out_dir, f) for f in out_files]
        newest_file = max(out_files_paths, key=os.path.getmtime)
        print("Newest output file path:", newest_file)
        
        # Open output PDF and read OCGs
        doc = fitz.open(newest_file)
        ocgs = doc.get_ocgs()
        print("Embedded OCG Layers in output PDF:")
        found_inspector_ocg = False
        for xref, info in ocgs.items():
            print(f"  - [{xref}] {info}")
            if isinstance(info, dict) and info.get("name") == "Vector PDF Inspector":
                found_inspector_ocg = True
            elif info == "Vector PDF Inspector":
                found_inspector_ocg = True
                
        doc.close()
        
        assert found_inspector_ocg, "Error: 'Vector PDF Inspector' layer was not found in the output PDF!"
        print("\nSUCCESS: 'Vector PDF Inspector' layer verified in output PDF OCGs list.")
    else:
        print("No patterns found to write to PDF.")
