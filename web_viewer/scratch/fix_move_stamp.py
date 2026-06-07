"""
Fix the corrupted move_stamp function in app.py.
Replace the broken route declaration and remove the duplicated tail code.
"""

with open(r'c:\pinchus\web_viewer\app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix 1: the broken route declaration at line 1289
old_route = '@app.route("/api/pdf/<path    data = request.json or {}'
new_route = '''@app.route("/api/pdf/<path:filename>/stamps/<int:xref>/move", methods=["PATCH"])
@api_login_required
def move_stamp(filename, xref):
    pdf_path = get_pdf_path(filename)
    if not pdf_path or not os.path.exists(pdf_path):
        return jsonify({"error": "File not found"}), 404

    data = request.json or {}'''

if old_route not in text:
    print("ERROR: could not find broken route declaration")
    exit(1)

text = text.replace(old_route, new_route, 1)

# Fix 2: remove the duplicated tail code that starts right after the first except block
bad_tail = '''    except Exception as e:
        import traceback
      os.replace(tmp_path, pdf_path)

        return jsonify({
            "success": True,
            "xref": result_xref,
            "page_num": int(page_num),
            "rect": result_rect,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500'''

good_tail = '''    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500'''

if bad_tail not in text:
    print("ERROR: could not find duplicated tail code")
    # show context
    idx = text.find('      os.replace(tmp_path, pdf_path)')
    print("Context:", repr(text[max(0,idx-200):idx+200]))
    exit(1)

text = text.replace(bad_tail, good_tail, 1)

with open(r'c:\pinchus\web_viewer\app.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Fixed successfully")
