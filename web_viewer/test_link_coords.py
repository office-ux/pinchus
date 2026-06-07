import fitz

doc = fitz.open(r"C:\pinchus\Sample pdfs\edited samples\DOC-20250715-WA0309_no_stamps_patterns_detected.pdf")
page = doc[0]

page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(100, 100, 200, 200), "uri": "https://test.com"})

for link in page.get_links():
    print(link)

doc.save(r"C:\pinchus\web_viewer\test_link.pdf")
