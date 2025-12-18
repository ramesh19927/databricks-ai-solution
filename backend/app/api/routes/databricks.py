from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.core.config import settings
from backend.app.db import models
from backend.app.schemas import DocumentIngestResponse
from backend.app.services.databricks import DatabricksIngestionService
from backend.app.services.documents import DocumentIngestionService

router = APIRouter(prefix="/databricks", tags=["databricks"])


@router.post("/ingest-table", response_model=DocumentIngestResponse)
def ingest_table(
    table: str,
    limit: int = 50,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(get_current_user),
):
    if not (settings.databricks_host and settings.databricks_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Databricks not configured")
    service = DatabricksIngestionService(
        host=settings.databricks_host,
        token=settings.databricks_token,
        http_path=settings.databricks_http_path,
        warehouse_id=settings.databricks_warehouse_id,
    )
    rows = service.fetch_table_sample(table, limit=limit)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No rows returned from Databricks")
    ingestion = DocumentIngestionService(db)
    document = ingestion.ingest_text_rows(rows, source=table, owner_id=current_user.id)
    return DocumentIngestResponse(document_id=document.id, chunk_count=len(document.chunks), source="databricks")
