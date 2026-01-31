from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from django.http import HttpResponse, FileResponse
from django.views.decorators.http import require_http_methods

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

from .models import PDF, PDFChunk

import PyPDF2
import pdfplumber
import numpy as np
import faiss
import json
import torch

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


# ---------------- Model Loading (runs on server startup) ----------------

embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

llm_model_name = "google/flan-t5-small"
tokenizer = AutoTokenizer.from_pretrained(llm_model_name)
llm_model = AutoModelForSeq2SeqLM.from_pretrained(llm_model_name)
device = "cuda" if torch.cuda.is_available() else "cpu"
llm_model = llm_model.to(device)


# ---------------- Utility Functions ----------------

def extract_text_from_pdf(file_obj) -> str:
    """
    Extract text from a PDF file using:
    1) PyPDF2 (fast, works for many)
    2) pdfplumber fallback (better for some PDFs)
    Returns "" if nothing extracted.
    """
    # 1) Try PyPDF2
    try:
        f = file_obj.open("rb") if hasattr(file_obj, "open") else file_obj
        reader = PyPDF2.PdfReader(f)
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)

        if hasattr(file_obj, "open"):
            f.close()

        merged = "\n".join(parts).strip()
        if merged:
            return merged
    except Exception as e:
        print("PyPDF2 error:", e)

    # 2) Fallback to pdfplumber
    try:
        f = file_obj.open("rb") if hasattr(file_obj, "open") else file_obj
        parts = []
        with pdfplumber.open(f) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)

        if hasattr(file_obj, "open"):
            f.close()

        return "\n".join(parts).strip()
    except Exception as e:
        print("pdfplumber error:", e)

    return ""


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 40):
    """
    Word-based overlapping chunking.
    chunk_size and overlap are in WORDS.
    """
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)
    chunks = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def vector_search(query_vec, chunk_embeds, top_k=5):
    """
    FAISS L2 search.
    chunk_embeds: list[np.array(float32)] with same dimension
    """
    if len(chunk_embeds) == 0:
        return [], []

    dim = chunk_embeds[0].shape[0]
    index = faiss.IndexFlatL2(dim)

    embeddings_np = np.array(chunk_embeds, dtype="float32")
    index.add(embeddings_np)

    top_k = min(top_k, len(chunk_embeds))
    distances, indices = index.search(np.array([query_vec], dtype="float32"), top_k)
    return indices[0], distances[0]


# ---------------- API Endpoints ----------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_pdf(request):
    file = request.FILES.get("file")

    if not file:
        return Response({"error": "No file provided"}, status=400)
    if not file.name.lower().endswith(".pdf"):
        return Response({"error": "Only PDF files allowed"}, status=400)

    try:
        file.seek(0)
        file_content = file.read()
        if not file_content:
            return Response({"error": "File is empty"}, status=400)

        pdf_file = ContentFile(file_content, name=file.name)
        pdf_obj = PDF.objects.create(
            user=request.user,
            file=pdf_file,
            title=file.name,
            processing_status=PDF.PROCESSING_PENDING,
        )

        # Kick off background processing to avoid long upload timeouts
        import threading

        def _bg_process(pdf_id):
            try:
                # fetch up-to-date object
                p = PDF.objects.get(id=pdf_id)
                p.processing_status = PDF.PROCESSING_RUNNING
                p.processing_error = None
                p.save()

                success, payload = process_pdf_obj(p)
                if success:
                    p.processing_status = PDF.PROCESSING_DONE
                    p.processing_error = None
                    from django.utils import timezone
                    p.processed_at = timezone.now()
                    p.save()
                else:
                    p.processing_status = PDF.PROCESSING_FAILED
                    p.processing_error = payload.get("error")
                    p.save()
            except Exception as e:
                try:
                    p = PDF.objects.get(id=pdf_id)
                    p.processing_status = PDF.PROCESSING_FAILED
                    p.processing_error = str(e)
                    p.save()
                except Exception:
                    pass

        t = threading.Thread(target=_bg_process, args=(pdf_obj.id,), daemon=True)
        t.start()

        return Response({
            "message": "PDF uploaded. Processing started",
            "pdf_id": pdf_obj.id,
            "file_url": f"/api/pdf/{pdf_obj.id}/view/",
            "chunks_url": f"/api/pdf_chunks/{pdf_obj.id}/",
            "ask_url": f"/api/ask_pdf/{pdf_obj.id}/",
        })
    except Exception as e:
        return Response({"error": f"Upload failed: {str(e)}"}, status=500)


def process_pdf_obj(pdf_obj):
    """
    Core processing logic for a PDF object:
    Extract text -> chunk -> embed -> save in DB.
    Returns (success: bool, payload: dict) where payload contains message or error and optional status.
    """
    try:
        text = extract_text_from_pdf(pdf_obj.file)
        if not text:
            return False, {"error": "Could not extract text from PDF", "status": 400}

        chunks = chunk_text(text, chunk_size=200, overlap=40)
        if not chunks:
            return False, {"error": "No chunks created from extracted text", "status": 400}

        # Clear old chunks
        PDFChunk.objects.filter(pdf=pdf_obj).delete()

        # Save new chunks
        created = 0
        for i, chunk_text_content in enumerate(chunks):
            try:
                embedding = embed_model.encode(chunk_text_content).tolist()
            except Exception as e:
                return False, {"error": f"Embedding generation failed: {str(e)}", "status": 500}

            PDFChunk.objects.create(
                pdf=pdf_obj,
                chunk_text=chunk_text_content,
                embedding=embedding,
                order=i,
                page_number=None,  # real page numbers require page-based extraction
            )
            created += 1

        return True, {"message": "PDF processed successfully", "chunks_created": created}
    except Exception as e:
        return False, {"error": f"Processing failed: {str(e)}", "status": 500}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_pdf(request, pdf_id):
    """
    Wrapper view around process_pdf_obj
    """
    try:
        pdf_obj = get_object_or_404(PDF, id=pdf_id, user=request.user)
        # mark running
        pdf_obj.processing_status = PDF.PROCESSING_RUNNING
        pdf_obj.processing_error = None
        pdf_obj.save()

        success, payload = process_pdf_obj(pdf_obj)
        if not success:
            pdf_obj.processing_status = PDF.PROCESSING_FAILED
            pdf_obj.processing_error = payload.get("error")
            pdf_obj.save()
            return Response(payload, status=payload.get("status", 500))

        pdf_obj.processing_status = PDF.PROCESSING_DONE
        from django.utils import timezone
        pdf_obj.processed_at = timezone.now()
        pdf_obj.save()
        return Response(payload)
    except Exception as e:
        try:
            pdf_obj.processing_status = PDF.PROCESSING_FAILED
            pdf_obj.processing_error = str(e)
            pdf_obj.save()
        except Exception:
            pass
        return Response({"error": f"Processing failed: {str(e)}"}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pdf_chunks(request, pdf_id):
    """
    Return all chunks of a PDF
    """
    try:
        pdf_obj = get_object_or_404(PDF, id=pdf_id, user=request.user)
        chunks = PDFChunk.objects.filter(pdf=pdf_obj).order_by("order")

        data = [
            {"id": c.id, "chunk_text": c.chunk_text, "order": c.order, "page_number": c.page_number}
            for c in chunks
        ]
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_pdfs(request):
    pdfs = PDF.objects.filter(user=request.user).order_by("-uploaded_at")
    data = [
        {
            "id": p.id,
            "title": p.title,
            "file_url": f"/api/pdf/{p.id}/view/",
            "processing_status": p.processing_status,
            "processing_error": p.processing_error,
        }
        for p in pdfs
    ]
    return Response(data)


@require_http_methods(["GET"])
def view_pdf(request, pdf_id):
    """
    Serve PDF with JWT auth (streams file)
    Your frontend must send Authorization: Bearer <token>
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Bearer "):
        return HttpResponse("Unauthorized", status=401)

    token = auth_header.split(" ")[1]

    # Validate JWT manually using SimpleJWT
    try:
        jwt_auth = JWTAuthentication()

        class FakeRequest:
            def __init__(self, token_str):
                self.META = {"HTTP_AUTHORIZATION": f"Bearer {token_str}"}

        fake_req = FakeRequest(token)
        auth_result = jwt_auth.authenticate(fake_req)

        if auth_result is None:
            return HttpResponse("Unauthorized", status=401)

        user, _ = auth_result
    except (InvalidToken, AuthenticationFailed) as e:
        return HttpResponse(f"Unauthorized: {str(e)}", status=401)

    # Get PDF owned by user
    pdf = get_object_or_404(PDF, id=pdf_id, user=user)

    # Stream file
    try:
        # Ensure file exists on storage before opening to avoid 500s
        if not pdf.file or not pdf.file.storage.exists(pdf.file.name):
            return HttpResponse("File not found on server", status=404)

        response = FileResponse(pdf.file.open("rb"), content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{pdf.title}"'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask_pdf(request, pdf_id):
    """
    Ask a question about a PDF using:
    - SentenceTransformer embeddings + FAISS retrieval
    - flan-t5-small generation using retrieved context
    """
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"error": "Question required"}, status=400)

    # Ensure PDF belongs to user (important security)
    pdf_obj = get_object_or_404(PDF, id=pdf_id, user=request.user)

    chunks_qs = PDFChunk.objects.filter(pdf=pdf_obj).order_by("order")
    if not chunks_qs.exists():
        # No chunks present — attempt synchronous processing to recover
        success, payload = process_pdf_obj(pdf_obj)
        if not success:
            # Return the processing error so frontend can surface it or allow manual reprocess
            return Response(payload, status=payload.get("status", 500))
        # Re-fetch chunks after processing
        chunks_qs = PDFChunk.objects.filter(pdf=pdf_obj).order_by("order")
        if not chunks_qs.exists():
            return Response({"error": "No chunks found after processing"}, status=500)

    q_embed = embed_model.encode(question)

    # Build (text, embedding) pairs ONLY for valid embeddings
    pairs = []
    for c in chunks_qs:
        emb = c.embedding
        if emb is None:
            continue
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except Exception:
                continue
        if not isinstance(emb, list) or len(emb) == 0:
            continue
        if not all(isinstance(x, (float, int)) for x in emb):
            continue

        pairs.append((c.chunk_text, np.array(emb, dtype="float32")))

    if len(pairs) == 0:
        return Response({"error": "No valid embeddings found"}, status=500)

    texts = [t for t, _ in pairs]
    embeds = [e for _, e in pairs]

    top_indices, _ = vector_search(q_embed, embeds, top_k=5)
    relevant_text = "\n\n".join([texts[i] for i in top_indices])

    prompt = f"""
You are an AI assistant for a PDF. Use ONLY the content below.

Relevant PDF Content:
----------------------
{relevant_text}

Question:
{question}

Answer clearly and concisely.
""".strip()

    inputs = tokenizer(prompt, return_tensors="pt", truncation=True).to(device)
    outputs = llm_model.generate(**inputs, max_new_tokens=200)
    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return Response({"answer": answer})