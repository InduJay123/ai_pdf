import PyPDF2
import pdfplumber
import os
p=os.path.join(os.path.dirname(__file__), '..', 'media', 'pdfs', 'Sri_Lanka.pdf')
print('path:', os.path.abspath(p))
print('exists:', os.path.exists(p))
# PyPDF2
try:
    with open(p,'rb') as f:
        reader=PyPDF2.PdfReader(f)
        sample=[]
        for page in reader.pages[:5]:
            t=page.extract_text()
            sample.append(t or '')
    s='\n'.join(sample)
    print('PyPDF2 extracted length:', len(s))
    print('PyPDF2 sample:', s[:500])
except Exception as e:
    print('PyPDF2 error:', e)
# pdfplumber
try:
    with pdfplumber.open(p) as pdf:
        sample2=[]
        for page in pdf.pages[:5]:
            t=page.extract_text()
            sample2.append(t or '')
    s2='\n'.join(sample2)
    print('pdfplumber extracted length:', len(s2))
    print('pdfplumber sample:', s2[:500])
except Exception as e:
    print('pdfplumber error:', e)
