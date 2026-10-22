import json

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import DocumentUploadForm
from .models import Document, DocumentChunk
from .services import embed_texts, extract_pages, generate_answer, retrieve_chunks, split_pages_into_chunks


def format_sources(ranked_chunks):
    return [
        {
            "filename": chunk.document.filename,
            "page": chunk.page_number,
            "text": chunk.text,
            "score": round(score, 3),
        }
        for chunk, score in ranked_chunks
    ]


def dashboard(request):
    return render(
        request,
        "documents/dashboard.html",
        {
            "documents": Document.objects.all().order_by("-uploaded_at"),
            "upload_form": DocumentUploadForm(),
            "max_upload_mb": settings.MAX_UPLOAD_BYTES // (1024 * 1024),
        },
    )


@require_POST
def upload_document(request):
    form = DocumentUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect("dashboard")

    uploaded_file = form.cleaned_data["file"]
    try:
        pages = extract_pages(uploaded_file.name, uploaded_file.read())
        chunks = split_pages_into_chunks(pages)
        if not chunks:
            messages.error(request, "No readable text was found in that file.")
            return redirect("dashboard")
        embeddings = embed_texts([text for _, text in chunks])
    except Exception as error:
        messages.error(request, f"Could not process this document: {error}")
        return redirect("dashboard")

    with transaction.atomic():
        document = Document.objects.create(filename=uploaded_file.name)
        DocumentChunk.objects.bulk_create(
            [
                DocumentChunk(
                    document=document,
                    text=text,
                    embedding=embedding,
                    chunk_index=index,
                    page_number=page_number,
                )
                for index, ((page_number, text), embedding) in enumerate(zip(chunks, embeddings))
            ]
        )
    messages.success(request, f"Indexed {uploaded_file.name} into {len(chunks)} searchable passages.")
    return redirect("dashboard")


@require_POST
def ask_question(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Send a valid JSON request."}, status=400)

    question = payload.get("question") if isinstance(payload, dict) else None
    if not isinstance(question, str) or not question.strip():
        return JsonResponse({"error": "Enter a question."}, status=400)
    question = question.strip()
    if len(question) > 1000:
        return JsonResponse({"error": "Questions must be 1,000 characters or fewer."}, status=400)

    chunks = list(DocumentChunk.objects.select_related("document").all())
    if not chunks:
        return JsonResponse({"error": "Upload a document before asking a question."}, status=400)

    try:
        ranked_chunks = retrieve_chunks(question, chunks)
    except Exception as error:
        return JsonResponse({"error": str(error), "sources": []}, status=503)

    # A low cosine similarity means the documents provide no useful evidence.
    if not ranked_chunks or ranked_chunks[0][1] < 0.25:
        return JsonResponse(
            {
                "answer": "I could not find information about that in the uploaded documents.",
                "sources": [],
            }
        )

    sources = format_sources(ranked_chunks)
    try:
        answer = generate_answer(question, ranked_chunks)
    except Exception as error:
        return JsonResponse({"error": str(error), "sources": sources}, status=503)
    return JsonResponse({"answer": answer, "sources": sources})


@require_POST
def delete_document(request, document_id):
    document = get_object_or_404(Document, pk=document_id)
    filename = document.filename
    document.delete()
    messages.success(request, f"Removed {filename} and its indexed passages.")
    return redirect("dashboard")
