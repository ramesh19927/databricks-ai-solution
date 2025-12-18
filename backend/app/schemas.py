from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentIngestResponse(BaseModel):
    document_id: UUID
    chunk_count: int
    source: str


class QueryRequest(BaseModel):
    query: str
    k: int = 4


class ChunkResult(BaseModel):
    id: UUID
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SOWRequest(BaseModel):
    project_id: str
    title: Optional[str] = None
    requirements: List[str]
    constraints: List[str] = Field(default_factory=list)
    tone: str = "professional"
    include_retrieval: bool = True
    query: Optional[str] = None


class SOWResponse(BaseModel):
    sow_id: UUID
    body: str
    created_at: datetime
