from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Document, DocumentChunk
from .services import split_pages_into_chunks


class ChunkingTests(TestCase):
    def test_chunks_overlap_and_keep_page_numbers(self):
        text = "a" * 1900
        chunks = split_pages_into_chunks([(4, text)])

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0][1][-150:], chunks[1][1][:150])
        self.assertTrue(all(page == 4 for page, _ in chunks))


class DocumentViewsTests(TestCase):
    def test_dashboard_renders(self):
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ask your documents anything.")

    @patch("documents.views.embed_texts", return_value=[[1.0, 0.0]])
    def test_upload_indexes_text_document(self, _embed_texts):
        upload = SimpleUploadedFile("notes.txt", b"RAG retrieves supporting passages.", content_type="text/plain")
        response = self.client.post(reverse("upload_document"), {"file": upload})

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(Document.objects.count(), 1)
        self.assertEqual(DocumentChunk.objects.count(), 1)
        self.assertEqual(DocumentChunk.objects.first().text, "RAG retrieves supporting passages.")

    def test_question_without_documents_returns_clear_error(self):
        response = self.client.post(
            reverse("ask_question"),
            data='{"question":"What is this about?"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Upload a document", response.json()["error"])

    def test_question_must_be_a_string(self):
        response = self.client.post(
            reverse("ask_question"),
            data='{"question":42}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    @patch("documents.views.retrieve_chunks", return_value=[])
    def test_unretrievable_answer_is_not_guessed(self, _retrieve_chunks):
        document = Document.objects.create(filename="notes.txt")
        DocumentChunk.objects.create(document=document, text="Some content", embedding=[1, 0], chunk_index=0)
        response = self.client.post(
            reverse("ask_question"),
            data='{"question":"What is the capital of Mars?"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("could not find", response.json()["answer"])
        self.assertEqual(response.json()["sources"], [])

    @patch("documents.views.generate_answer", side_effect=RuntimeError("Configure Gemini"))
    @patch("documents.views.retrieve_chunks")
    def test_generation_error_still_returns_retrieved_sources(self, retrieve, _generate):
        document = Document.objects.create(filename="notes.txt")
        chunk = DocumentChunk.objects.create(document=document, text="Supporting evidence", embedding=[1, 0], chunk_index=0)
        retrieve.return_value = [(chunk, 0.8)]
        response = self.client.post(
            reverse("ask_question"),
            data='{"question":"What is supported?"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["sources"][0]["text"], "Supporting evidence")
