from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.db import models
from backend.app.schemas import DocumentIngestResponse, QueryRequest, ChunkResult
from backend.app.services.documents import DocumentIngestionService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentIngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(get_current_user),
):
    contents = await file.read()
    ingestion = DocumentIngestionService(db)
    try:
        document = ingestion.ingest_upload(contents, file.filename, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DocumentIngestResponse(document_id=document.id, chunk_count=len(document.chunks), source=document.source)


@router.post("/search", response_model=list[ChunkResult])
def search_documents(
    request: QueryRequest,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(get_current_user),
):
    ingestion = DocumentIngestionService(db)
    results = ingestion.search(request.query, request.k)
    return [ChunkResult(id=item["id"], content=item["content"], metadata=item["metadata"], score=item["score"]) for item in results]
