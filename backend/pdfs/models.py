from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class PDF(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    file=models.FileField(upload_to="pdfs/")
    title=models.CharField(max_length=255)
    uploaded_at=models.DateTimeField(auto_now_add=True)

    # Processing status fields
    PROCESSING_PENDING = "pending"
    PROCESSING_RUNNING = "processing"
    PROCESSING_DONE = "done"
    PROCESSING_FAILED = "failed"

    PROCESSING_STATUS_CHOICES = [
        (PROCESSING_PENDING, "Pending"),
        (PROCESSING_RUNNING, "Processing"),
        (PROCESSING_DONE, "Done"),
        (PROCESSING_FAILED, "Failed"),
    ]

    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default=PROCESSING_PENDING)
    processing_error = models.TextField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

class PDFChunk(models.Model):
    pdf = models.ForeignKey(PDF, on_delete=models.CASCADE)
    chunk_text = models.TextField()
    embedding = models.JSONField(null=True, blank=True)
    page_number = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(default=0) 
    created_at = models.DateTimeField(auto_now_add=True)