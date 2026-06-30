"""
apply_stamp_shapes.py
=====================
PURELY GRAPHICAL — does NOT touch the database or annotation metadata.

For every Stamp annotation listed in `updates`, this module:
  1. Extracts the /AP (Appearance Stream) XObject from the source shape PDF.
     (This pulls *only* the stamp vector, ignoring any full-page background data).
  2. Builds a composite Form XObject that contains both the shape vector
     and the stamp's number text centered inside.
  3. Injects this composite XObject directly into the existing target
     annotation's /AP dictionary.

This ensures:
  - It remains a true, clickable/draggable Stamp annotation (not flattened).
  - Subsequent updates cleanly replace the appearance stream (no numbers stacking).
  - The vector shape scales perfectly to the target bounding box.

No PatternName / NM / StampID writes are made.
All database changes are handled by stamp_db.apply_rule_updates() in app.py.

Called from app.py's /api/manage_tags/apply_rules endpoint.
Runs in a background daemon thread so the HTTP response returns immediately.

Usage
-----
    from apply_stamp_shapes import apply_shapes_background

    # updates = list of dicts with keys:
    #   pattern_name, pdf_path, xref, page
    apply_shapes_background(updates, global_stamps_dir)
"""

import os
import re
import threading
import traceback
from collections import defaultdict

import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def apply_shapes_background(updates: list, global_stamps_dir: str) -> threading.Thread:
    """
    Fire-and-forget: launch a daemon thread that applies vector shapes
    to all PDFs referenced in `updates`.

    Parameters
    ----------
    updates : list[dict]
        Each dict must contain:
            pattern_name  – e.g. "User_1756"  (base_shape="User", num="1756")
            pdf_path      – absolute path to the target PDF
            xref          – int xref of the existing Stamp annotation (may be 0)
            page          – 1-based page number
    global_stamps_dir : str
        Folder that contains  <ShapeName>.pdf  files.

    Returns
    -------
    threading.Thread  – already started daemon thread (useful for testing).
    """
    # Only queue updates that have all required keys.
    # NOTE: xref can legitimately be 0, so check for None explicitly.
    pdf_map = defaultdict(list)
    queued = 0
    for upd in updates:
        has_pattern = "pattern_name" in upd and upd.get("pattern_name")
        has_path    = upd.get("pdf_path")
        has_xref    = upd.get("xref") is not None   # 0 is a valid xref
        has_page    = upd.get("page")
        if has_pattern and has_path and has_xref and has_page:
            pdf_map[upd["pdf_path"]].append(upd)
            queued += 1

    print(f"[apply_shapes] queued {queued} shape updates across {len(pdf_map)} PDF(s)")

    t = threading.Thread(
        target=_apply_pdf_shapes,
        args=(dict(pdf_map), global_stamps_dir),
        daemon=True,
    )
    t.start()
    return t


# ---------------------------------------------------------------------------
# Worker (runs in background thread)
# ---------------------------------------------------------------------------

def _apply_pdf_shapes(pdf_map: dict, global_stamps_dir: str):
    """Write vector shapes into each PDF referenced in pdf_map."""
    if not pdf_map:
        print("[apply_shapes] nothing to do — pdf_map is empty")
        return

    for pdf_path, shape_upds in pdf_map.items():
        if not os.path.exists(pdf_path):
            print(f"[apply_shapes] skip – not found: {pdf_path}")
            continue
        try:
            _process_one_pdf(pdf_path, shape_upds, global_stamps_dir)
        except Exception as exc:
            print(f"[apply_shapes] FAILED {pdf_path}: {exc}")
            traceback.print_exc()


def _process_one_pdf(pdf_path: str, shape_upds: list, global_stamps_dir: str):
    """Open one target PDF and apply shapes to all matching annotations using perfectly scaled Composite XObjects."""
    print(f"[apply_shapes] processing {pdf_path}  ({len(shape_upds)} stamps)")
    doc = fitz.open(pdf_path)
    pdf_changed = False

    # ------------------------------------------------------------------
    # Cache shape XObject xrefs so each base shape is imported only once
    # Key: base_shape name   Value: int (xref) or None
    # ------------------------------------------------------------------
    shape_xobj_cache: dict = {}

    def get_shape_xobj_xref(base_shape: str):
        if base_shape in shape_xobj_cache:
            return shape_xobj_cache[base_shape]
            
        spdf = os.path.join(global_stamps_dir, f"{base_shape}.pdf")
        if not os.path.exists(spdf):
            print(f"[apply_shapes] shape PDF not found: {spdf}")
            shape_xobj_cache[base_shape] = None
            return None
            
        shape_xobj_xref = None
        try:
            src = fitz.open(spdf)
            
            # Find which page in the source PDF actually contains the Stamp annotation
            src_page_idx = 0
            for i in range(len(src)):
                has_stamp = False
                for a in src[i].annots() or []:
                    if a.type[1] == "Stamp":
                        has_stamp = True
                        break
                if has_stamp:
                    src_page_idx = i
                    break

            # Insert ONLY that single page, ensuring annotations are copied
            doc.insert_pdf(src, from_page=src_page_idx, to_page=src_page_idx, annots=True)
            src.close()
            
            tmp_page = doc[-1]

            # Strategy 1: Find the Stamp annotation on the inserted page and extract its /AP /N stream
            for ca in tmp_page.annots() or []:
                if ca.type[1] == "Stamp":
                    ap = doc.xref_get_key(ca.xref, "AP")
                    if ap[0] == "dict":
                        nm = re.search(r'/N\s+(\d+)\s+0\s+R', ap[1])
                        shape_xobj_xref = int(nm.group(1)) if nm else ca.xref
                        break

            # Strategy 2: Fall back to wrapping the whole page's content stream into a Form XObject
            if not shape_xobj_xref:
                res2 = doc.xref_get_key(tmp_page.xref, "Resources")
                tmp_page.clean_contents()
                cl = tmp_page.get_contents()
                if cl:
                    cs = doc.xref_stream(cl[0])
                    b = tmp_page.rect
                    shape_xobj_xref = doc.get_new_xref()
                    od = f"<< /Type /XObject /Subtype /Form /BBox [{b.x0} {b.y0} {b.x1} {b.y1}] /Matrix [1 0 0 1 0 0] "
                    if res2[0] in ("dict", "xref"):
                        od += f"/Resources {res2[1]} "
                    od += ">>"
                    doc.update_object(shape_xobj_xref, od)
                    doc.update_stream(shape_xobj_xref, cs)

            # Cleanly remove the single temporary page we inserted
            doc.delete_page(-1)
            
            shape_xobj_cache[base_shape] = shape_xobj_xref
            return shape_xobj_xref
        except Exception as _e:
            print(f"[apply_shapes] error extracting XObject for '{base_shape}': {_e}")
            shape_xobj_cache[base_shape] = None
            return None

    # ------------------------------------------------------------------
    # Pre-fetch all required shape XObjects before iterating pages.
    # ------------------------------------------------------------------
    needed_base_shapes = set()
    for u in shape_upds:
        pn = u["pattern_name"]
        m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', pn)
        needed_base_shapes.add(m.group(1) if m else pn)

    for base_shape in needed_base_shapes:
        get_shape_xobj_xref(base_shape)

    # ------------------------------------------------------------------
    # Apply updates directly via xref manipulation (no page iteration)
    # ------------------------------------------------------------------
    for u in shape_upds:
        ann_xref = int(u["xref"])
        
        # 1. Parse Rect from target xref to get width and height (optional now, since viewer handles scaling)
        rect_obj = doc.xref_get_key(ann_xref, "Rect")
        if rect_obj[0] != "array":
            continue

        pn = u["pattern_name"]
        m = re.search(r'^(.*)[_\s\-]([^_\s\-]+)$', pn)
        base_shape = m.group(1) if m else pn
        num_text   = m.group(2) if m else "1"

        shape_xobj_xref = get_shape_xobj_xref(base_shape)
        if not shape_xobj_xref:
            continue

        # Calculate the exact bounding box of the shape after its own Matrix is applied.
        # When we execute /ShapeForm Do, it applies its Matrix to its BBox.
        # Our Composite XObject must wrap this exact output area, so we don't double-apply the Matrix!
        bbox_raw = doc.xref_get_key(shape_xobj_xref, "BBox")
        mat_raw = doc.xref_get_key(shape_xobj_xref, "Matrix")
        
        shape_rect = fitz.Rect(0, 0, 20, 20)
        if bbox_raw[0] != "null":
            try:
                bvals = list(map(float, bbox_raw[1].strip("[]").split()))
                if len(bvals) == 4:
                    shape_rect = fitz.Rect(bvals)
                    if mat_raw[0] != "null":
                        mvals = list(map(float, mat_raw[1].strip("[]").split()))
                        shape_rect = shape_rect * fitz.Matrix(mvals)
            except:
                pass
                
        bx0, by0 = shape_rect.x0, shape_rect.y0
        sw, sh = shape_rect.width, shape_rect.height
                
        # Calculate perfectly centered text relative to the shape's actual drawn area
        fs = max(min(sw, sh) * 0.5, 6.0)
        try:
            text_len = fitz.get_text_length(num_text, fontname="helv", fontsize=fs)
        except:
            text_len = len(num_text) * fs * 0.55
            
        tx = bx0 + (sw / 2) - (text_len / 2)
        ty = by0 + (sh - fs) / 2 + (fs * 0.2) # Nudge up for baseline

        stream = (
            f"q /ShapeForm Do Q\n"
            f"BT /Helv {fs:g} Tf 1 0 0 rg {tx:g} {ty:g} Td ({num_text}) Tj ET\n"
        ).encode("latin1")

        # The composite XObject natively bounds the output of ShapeForm, so it needs NO Matrix of its own.
        bbox_str = f"[{bx0} {by0} {bx0+sw} {by0+sh}]"
        
        res_dict = (
            f"<< /XObject << /ShapeForm {shape_xobj_xref} 0 R >>"
            f" /Font << /Helv << /Type /Font /Subtype /Type1"
            f" /BaseFont /Helvetica >> >> >>"
        )
        
        comp_xref = doc.get_new_xref()
        comp_dict = f"<< /Type /XObject /Subtype /Form /BBox {bbox_str} /Matrix [1 0 0 1 0 0] /Resources {res_dict} >>"

        doc.update_object(comp_xref, comp_dict)
        doc.update_stream(comp_xref, stream)

        # Inject the composite stream directly into the existing annotation's Appearance dictionary
        doc.xref_set_key(ann_xref, "AS", "null")
        doc.xref_set_key(ann_xref, "AP", f"<< /N {comp_xref} 0 R >>")
        doc.xref_set_key(ann_xref, "Subtype", "/Stamp")
        pdf_changed = True
        print(f"[apply_shapes]   ✓ injected '{base_shape}' + '{num_text}' into xref {ann_xref}")

    # ------------------------------------------------------------------
    # Save the modified PDF
    # ------------------------------------------------------------------
    if pdf_changed:
        try:
            doc.saveIncr()
        except Exception:
            # Incremental save failed (e.g. linearised PDF) — full save
            tmp_path = pdf_path + ".tmp"
            doc.save(tmp_path, deflate=True)
            os.replace(tmp_path, pdf_path)
        print(f"[apply_shapes] saved → {pdf_path}")
    else:
        print(f"[apply_shapes] no changes made to {pdf_path}")

    doc.close()
