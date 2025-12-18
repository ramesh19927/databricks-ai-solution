from datetime import datetime
from textwrap import dedent
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db import models
from backend.app.services.embedding import EmbeddingService


class SowService:
    def __init__(self, db: Session, embedding_service: Optional[EmbeddingService] = None) -> None:
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService(api_key=settings.openai_api_key)
        self.client = self.embedding_service._get_openai_client()  # reuse client creation

    def generate(
        self,
        project_id: str,
        title: Optional[str],
        requirements: List[str],
        constraints: List[str],
        context_snippets: List[str],
        tone: str = "professional",
        owner_id: Optional[UUID] = None,
    ) -> models.SOWDocument:
        prompt = self._build_prompt(project_id, requirements, constraints, context_snippets, tone)
        if self.client:
            response = self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert delivery lead creating structured SOWs."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.25,
            )
            body = response.choices[0].message.content or ""
        else:
            body = prompt

        sow = models.SOWDocument(
            project_id=project_id,
            title=title or "Statement of Work",
            body=body,
            metadata={"requirements": requirements, "constraints": constraints},
            owner_id=owner_id,
            created_at=datetime.utcnow(),
        )
        self.db.add(sow)
        self.db.commit()
        self.db.refresh(sow)
        return sow

    def _build_prompt(
        self,
        project_id: str,
        requirements: List[str],
        constraints: List[str],
        snippets: List[str],
        tone: str,
    ) -> str:
        requirement_text = "\n- ".join(requirements)
        constraint_text = "\n- ".join(constraints) if constraints else "None provided"
        context_text = "\n---\n".join(snippets) if snippets else "No retrieved context"
        return dedent(
            f"""
            Create a structured Statement of Work for project {project_id} in a {tone} tone.
            Include executive summary, scope, deliverables, milestones, assumptions, dependencies,
            acceptance criteria, and a RACI table. Use bullet lists where helpful.

            Requirements:
            - {requirement_text}

            Constraints:
            - {constraint_text}

            Retrieved context:
            {context_text}
            """
        ).strip()
