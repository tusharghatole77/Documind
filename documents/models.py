from django.db import models


class Document(models.Model):
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename


class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    embedding = models.JSONField()
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_document_chunk_index",
            )
        ]

    def __str__(self):
        return f"{self.document.filename} · chunk {self.chunk_index + 1}"
