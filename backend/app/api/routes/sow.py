from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_current_user, get_db_session
from backend.app.db import models
from backend.app.schemas import ChunkResult, SOWRequest, SOWResponse
from backend.app.services.documents import DocumentIngestionService
from backend.app.services.sow import SowService

router = APIRouter(prefix="/sow", tags=["sow"])


@router.post("/generate", response_model=SOWResponse)
def generate_sow(
    request: SOWRequest,
    db: Session = Depends(get_db_session),
    current_user: models.User = Depends(get_current_user),
):
    documents = DocumentIngestionService(db)
    context = []
    if request.include_retrieval and request.query:
        context = documents.search(request.query, k=5)
    snippets = [item["content"] for item in context]

    service = SowService(db)
    sow = service.generate(
        project_id=request.project_id,
        title=request.title,
        requirements=request.requirements,
        constraints=request.constraints,
        context_snippets=snippets,
        tone=request.tone,
        owner_id=current_user.id,
    )
    return SOWResponse(sow_id=sow.id, body=sow.body, created_at=sow.created_at)


@router.get("/recent", response_model=list[SOWResponse])
def list_sows(db: Session = Depends(get_db_session), current_user: models.User = Depends(get_current_user)):
    sows = db.query(models.SOWDocument).order_by(models.SOWDocument.created_at.desc()).limit(10).all()
    return [SOWResponse(sow_id=item.id, body=item.body, created_at=item.created_at) for item in sows]
