import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db import models
from backend.app.services.embedding import EmbeddingService
from src.services.document_service import DocumentProcessor


class DocumentIngestionService:
    def __init__(self, db: Session, embedding_service: Optional[EmbeddingService] = None) -> None:
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self.processor = DocumentProcessor(databricks_host=None, token=None)

    def ingest_upload(self, file_bytes: bytes, filename: str, owner_id: Optional[UUID]) -> models.Document:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = Path(tmp.name)
        try:
            record = self.processor.process_file(str(tmp_path))
            chunks = self.processor.build_chunks(record)
        finally:
            tmp_path.unlink(missing_ok=True)

        document = models.Document(title=record.get("file_name") or filename, source="upload", owner_id=owner_id)
        self.db.add(document)
        self.db.flush()

        embedding_vectors = self._build_embeddings(chunks)
        for chunk, embedding in zip(chunks, embedding_vectors, strict=False):
            chunk_model = models.DocumentChunk(
                document_id=document.id, content=chunk["content"], metadata=chunk.get("metadata", {}), embedding=embedding
            )
            self.db.add(chunk_model)
        self.db.commit()
        self.db.refresh(document)
        return document

    def ingest_text_rows(self, rows: Iterable[Dict[str, str]], source: str, owner_id: Optional[UUID]) -> models.Document:
        content = "\n".join([", ".join(f"{k}: {v}" for k, v in row.items()) for row in rows])
        chunks = self.processor.build_chunks({"content": content, "file_name": source, "format": "text"})
        document = models.Document(title=source, source="databricks", owner_id=owner_id)
        self.db.add(document)
        self.db.flush()

        embedding_vectors = self._build_embeddings(chunks)
        for chunk, embedding in zip(chunks, embedding_vectors, strict=False):
            chunk_model = models.DocumentChunk(
                document_id=document.id, content=chunk["content"], metadata=chunk.get("metadata", {}), embedding=embedding
            )
            self.db.add(chunk_model)
        self.db.commit()
        self.db.refresh(document)
        return document

    def search(self, query: str, k: int = 4) -> List[Dict]:
        embed = self.embedding_service.embed(query)
        column_type = models.DocumentChunk.embedding.property.columns[0].type
        uses_vector = hasattr(column_type, "dim")

        if not uses_vector:
            chunks = self.db.execute(select(models.DocumentChunk)).scalars().all()
            results = []
            for chunk in chunks:
                score = self._cosine_similarity(embed, chunk.embedding or [0.0 for _ in embed])
                results.append({"id": chunk.id, "content": chunk.content, "metadata": chunk.metadata, "score": score})
            return sorted(results, key=lambda r: r["score"], reverse=True)[:k]

        stmt = select(models.DocumentChunk).order_by(models.DocumentChunk.embedding.op("<->")(embed)).limit(k)
        records = self.db.execute(stmt).scalars().all()
        return [{"id": rec.id, "content": rec.content, "metadata": rec.metadata, "score": 1.0} for rec in records]

    def _build_embeddings(self, chunks: List[Dict]) -> List[List[float]]:
        embeddings = []
        for chunk in chunks:
            embeddings.append(self.embedding_service.embed(chunk.get("content", "")))
        return embeddings

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
