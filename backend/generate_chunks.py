#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pdfchat.settings')
django.setup()

from pdfs.models import PDF, PDFChunk
from pdfs.views import extract_text_from_pdf, chunk_text

pdfs = PDF.objects.all()
print('Generating chunks for all PDFs...\n')

for pdf in pdfs:
    chunk_count = PDFChunk.objects.filter(pdf=pdf).count()
    
    if chunk_count > 0:
        print(f'✓ PDF {pdf.id}: {pdf.title} - Already has {chunk_count} chunks')
        continue
    
    try:
        print(f'→ PDF {pdf.id}: {pdf.title}...')
        text = extract_text_from_pdf(pdf.file)
        
        if not text or len(text) < 10:
            print(f'  ✗ No readable text extracted (length: {len(text) if text else 0})')
            continue
        
        chunks = chunk_text(text)
        PDFChunk.objects.filter(pdf=pdf).delete()
        
        for chunk_content in chunks:
            PDFChunk.objects.create(pdf=pdf, chunk_text=chunk_content)
        
        new_count = PDFChunk.objects.filter(pdf=pdf).count()
        print(f'  ✓ Created {new_count} chunks from {len(text)} characters')
        
    except Exception as e:
        print(f'  ✗ Error: {e}')

print('\nDone! Verifying...')
for pdf in PDF.objects.all():
    count = PDFChunk.objects.filter(pdf=pdf).count()
    print(f'  PDF {pdf.id}: {count} chunks')
