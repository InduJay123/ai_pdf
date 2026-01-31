from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from .models import PDF, PDFChunk
import PyPDF2
import numpy as np
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import faiss
import json

# Load embedding model
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Load Hugging Face LLM (CPU-friendly)
llm_model_name = "google/flan-t5-small"
tokenizer = AutoTokenizer.from_pretrained(llm_model_name)
llm_model = AutoModelForSeq2SeqLM.from_pretrained(llm_model_name)
device = "cuda" if torch.cuda.is_available() else "cpu"
llm_model = llm_model.to(device)

# ---------------- Utility Functions ----------------

def extract_text_from_pdf(file_obj):
    """Extract text from PDF file"""
    try:
        if hasattr(file_obj, 'open'):
            f = file_obj.open('rb')
        else:
            f = file_obj
        pdf_reader = PyPDF2.PdfReader(f)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if hasattr(file_obj, 'open'):
            f.close()
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks"""
    if not text:
        return []
    words = text.split()
    chunks = []
    current_chunk = []
    for word in words:
        current_chunk.append(word)
        if len(' '.join(current_chunk)) >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = current_chunk[-(overlap // 10):]  # overlap
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

def vector_search(query_vec, chunk_embeds, top_k=5):
    """Search top-k closest embeddings using FAISS"""
    if len(chunk_embeds) == 0:
        return [], []
    dim = chunk_embeds[0].shape[0]
    index = faiss.IndexFlatL2(dim)
    embeddings_np = np.array(chunk_embeds).astype("float32")
    index.add(embeddings_np)
    distances, indices = index.search(np.array([query_vec]).astype("float32"), top_k)
    return indices[0], distances[0]

# ---------------- API Endpoints ----------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_pdf(request):
    file = request.FILES.get("file")

    if not file:
        return Response({"error": "No file provided"}, status=400)
    if not file.name.endswith(".pdf"):
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
            title=file.name
        )
        
        process_pdf(request, pdf_obj.id)

        return Response({
            "message": "PDF uploaded successfully",
            "file_url": f"/api/pdf/{pdf_obj.id}/view/",
            "process_url": f"/api/pdf/{pdf_obj.id}/process/"
        })
    except Exception as e:
        return Response({"error": f"Upload failed: {str(e)}"}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_pdf(request, pdf_id):
    """Extract text from PDF, create chunks, and save embeddings"""
    try:
        pdf_obj = get_object_or_404(PDF, id=pdf_id, user=request.user)
        text = extract_text_from_pdf(pdf_obj.file)
        if not text:
            return Response({"error": "Could not extract text"}, status=400)

        chunks = chunk_text(text)
        PDFChunk.objects.filter(pdf=pdf_obj).delete()

        for i, chunk_text_content in enumerate(chunks):
            embedding = embed_model.encode(chunk_text_content).tolist()
            PDFChunk.objects.create(
                pdf=pdf_obj,
                chunk_text=chunk_text_content,
                embedding=embedding,
                order=i,
                page_number=i+1
            )

        return Response({"message": "PDF processed successfully", "chunks_created": len(chunks)})
    except Exception as e:
        return Response({"error": f"Processing failed: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pdf_chunks(request, pdf_id):
    """Return all chunks of a PDF"""
    try:
        pdf_obj = get_object_or_404(PDF, id=pdf_id, user=request.user)
        chunks = PDFChunk.objects.filter(pdf=pdf_obj)
        data = [{"id": c.id, "chunk_text": c.chunk_text} for c in chunks]
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_pdfs(request):
    pdfs = PDF.objects.filter(user=request.user)
    data = [{"id": p.id, "title": p.title, "file_url": f"/api/pdf/{p.id}/view/"} for p in pdfs]
    return Response(data)


@require_http_methods(["GET"])
def view_pdf(request, pdf_id):
    """Serve PDF with JWT authentication"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return HttpResponse("Unauthorized", status=401)
    token = auth_header.split(' ')[1]
    try:
        jwt_auth = JWTAuthentication()
        class FakeRequest:
            def __init__(self, token_str):
                self.META = {'HTTP_AUTHORIZATION': f'Bearer {token_str}'}
        fake_req = FakeRequest(token)
        auth_result = jwt_auth.authenticate(fake_req)
        if auth_result is None:
            return HttpResponse("Unauthorized", status=401)
        user, _ = auth_result
    except (InvalidToken, AuthenticationFailed) as e:
        return HttpResponse(f"Unauthorized: {str(e)}", status=401)
    
    try:
        pdf = PDF.objects.get(id=pdf_id, user=user)
    except PDF.DoesNotExist:
        return HttpResponse("Not found", status=404)

    try:
        with pdf.file.open('rb') as f:
            file_content = f.read()
        response = HttpResponse(file_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf.title}"'
        response['Content-Length'] = len(file_content)
        response['Cache-Control'] = 'public, max-age=3600'
        return response
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ask_pdf(request, pdf_id):
    """Ask a question about a PDF"""
    question = request.data.get("question", "")
    if not question:
        return Response({"error": "Question required"}, status=400)

    chunks = PDFChunk.objects.filter(pdf_id=pdf_id)
    if not chunks.exists():
        return Response({"error": "No chunks found"}, status=404)

    q_embed = embed_model.encode(question)

    chunk_texts = [c.chunk_text for c in chunks]
    chunk_embeds = []

    for c in chunks:
        emb = c.embedding
        if emb is None:
            continue
        if isinstance(emb, str):
            try:
                emb = json.loads(emb)
            except:
                continue
        if not isinstance(emb, list) or len(emb) == 0:
            continue
        if not all(isinstance(x, (float, int)) for x in emb):
            continue
        chunk_embeds.append(np.array(emb, dtype="float32"))

    if len(chunk_embeds) == 0:
        return Response({"error": "No valid embeddings found"}, status=500)

    top_indices, _ = vector_search(q_embed, chunk_embeds, top_k=5)
    relevant_text = "\n\n".join([chunk_texts[i] for i in top_indices])

    prompt = f"""
You are an AI assistant for a PDF. Use ONLY the content below.

Relevant PDF Content:
----------------------
{relevant_text}

Question:
{question}

Answer clearly and concisely.
"""
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    outputs = llm_model.generate(**inputs, max_new_tokens=200)
    answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

    return Response({"answer": answer})
