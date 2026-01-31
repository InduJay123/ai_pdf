from django.urls import path
from .views import upload_pdf, my_pdfs, view_pdf, process_pdf, pdf_chunks, ask_pdf

urlpatterns = [
    path('upload_pdf/', upload_pdf),
    path('my_pdfs/', my_pdfs),
    path('pdf/<int:pdf_id>/view/', view_pdf),
    path('pdf/<int:pdf_id>/process/', process_pdf),
    path("pdf_chunks/<int:pdf_id>/", pdf_chunks),
    path("ask_pdf/<int:pdf_id>/", ask_pdf),
]