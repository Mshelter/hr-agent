"""Local PostgreSQL service for job descriptions."""

import logging
import math
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import func, select

from app.models.recruitment import JobDescription, ScoringCriteria
from app.schemas.job_description import (
    JobDescriptionCreate,
    JobDescriptionResponse,
    JobDescriptionUpdate,
)

logger = logging.getLogger(__name__)


class JobDescriptionService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _status_value(value):
        return value.value if hasattr(value, "value") else value

    async def _owned_job(self, jd_id: str | UUID, user_id: UUID) -> JobDescription:
        try:
            resource_id = UUID(str(jd_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("职位描述不存在") from exc
        result = await self.db.execute(
            select(JobDescription).where(
                JobDescription.id == resource_id,
                JobDescription.user_id == user_id,
                JobDescription.is_active.is_(True),
            )
        )
        job = result.scalar_one_or_none()
        if not job:
            raise ValueError("职位描述不存在或无权限访问")
        return job

    async def create_job_description(
        self, jd_data: JobDescriptionCreate, user_id: UUID
    ) -> JobDescriptionResponse:
        payload = jd_data.model_dump()
        payload["status"] = self._status_value(payload.get("status")) or "draft"
        payload["workflow_type"] = payload.get("workflow_type") or "jd_generation"
        job = JobDescription(**payload, user_id=user_id, created_by=user_id, updated_by=user_id)
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        logger.info("成功创建本地职位描述: %s - %s", job.id, job.title)
        return JobDescriptionResponse.model_validate(job)

    async def update_job_description(
        self, jd_id: str, jd_data: JobDescriptionUpdate, user_id: UUID
    ) -> JobDescriptionResponse:
        job = await self._owned_job(jd_id, user_id)
        payload = jd_data.model_dump(exclude_unset=True)
        if "status" in payload:
            payload["status"] = self._status_value(payload["status"])
        for key, value in payload.items():
            setattr(job, key, value)
        job.updated_by = user_id
        await self.db.commit()
        await self.db.refresh(job)
        return JobDescriptionResponse.model_validate(job)

    async def get_job_description(
        self, jd_id: str, user_id: UUID
    ) -> JobDescriptionResponse:
        return JobDescriptionResponse.model_validate(await self._owned_job(jd_id, user_id))

    async def list_job_descriptions(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 10,
        status_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        filters = [
            JobDescription.user_id == user_id,
            JobDescription.is_active.is_(True),
        ]
        if status_filter:
            filters.append(JobDescription.status == status_filter)
        total = (
            await self.db.execute(select(func.count(JobDescription.id)).where(*filters))
        ).scalar() or 0
        result = await self.db.execute(
            select(JobDescription)
            .where(*filters)
            .order_by(JobDescription.updated_at.desc(), JobDescription.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = [JobDescriptionResponse.model_validate(item) for item in result.scalars().all()]
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": math.ceil(total / size) if total else 0,
        }

    async def delete_job_description(self, jd_id: str, user_id: UUID) -> Dict[str, Any]:
        job = await self._owned_job(jd_id, user_id)
        criteria_result = await self.db.execute(
            select(ScoringCriteria).where(
                ScoringCriteria.job_description_id == job.id,
                ScoringCriteria.user_id == user_id,
                ScoringCriteria.is_active.is_(True),
            )
        )
        deleted_criteria = []
        for criteria in criteria_result.scalars().all():
            criteria.is_active = False
            criteria.updated_by = user_id
            deleted_criteria.append({"id": str(criteria.id), "title": criteria.title})
        job.is_active = False
        job.updated_by = user_id
        await self.db.commit()
        return {
            "message": "职位描述已删除",
            "id": str(job.id),
            "deleted_scoring_criteria": deleted_criteria,
            "scoring_criteria_failures": [],
        }
