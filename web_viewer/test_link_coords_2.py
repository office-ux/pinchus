import fitz
import pprint

doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]

page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(100, 100, 200, 200), "uri": "https://test.com"})
doc.save(r"C:\pinchus\web_viewer\test_link.pdf")
doc.close()

doc2 = fitz.open(r"C:\pinchus\web_viewer\test_link.pdf")
page2 = doc2[0]
for lnk in page2.get_links():
    if lnk.get("uri") == "https://test.com":
        print("Link from:", lnk.get("from"))
