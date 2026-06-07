import fitz
doc = fitz.open(r'C:\pinchus\Projects\321654\pdfs\QCC_Mechanical___Plumbing___Fire_Drawings.pdf')
page = doc[0]
content = page.read_contents()
# Search for something related to the white box, like its coordinates or 'rg'/'RG' for white
print("Total content length:", len(content))
# Let's count how many times white color is set
import re
print("White fill commands (1 1 1 rg):", len(re.findall(b'1 1 1 rg', content)))
print("White fill commands (1 1 1 RG):", len(re.findall(b'1 1 1 RG', content)))
print("Overprint flag OPM:", len(re.findall(b'/OPM', content)))
print("Overprint flag OP:", len(re.findall(b'/OP ', content)))
