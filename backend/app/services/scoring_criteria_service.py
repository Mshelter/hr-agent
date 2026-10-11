"""Local PostgreSQL service for resume scoring criteria."""

import math
from typing import Dict, Optional
from uuid import UUID

from sqlalchemy import func, select

from app.models.recruitment import JobDescription, ScoringCriteria
from app.schemas.scoring_criteria import (
    ScoringCriteriaCreate,
    ScoringCriteriaListResponse,
    ScoringCriteriaResponse,
    ScoringCriteriaUpdate,
)


class ScoringCriteriaService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _status_value(value):
        return value.value if hasattr(value, "value") else value

    async def _owned_criteria(self, criteria_id: str | UUID, user_id: UUID) -> ScoringCriteria:
        try:
            resource_id = UUID(str(criteria_id))
        except (TypeError, ValueError) as exc:
            raise ValueError("评分标准不存在") from exc
        result = await self.db.execute(
            select(ScoringCriteria).where(
                ScoringCriteria.id == resource_id,
                ScoringCriteria.user_id == user_id,
                ScoringCriteria.is_active.is_(True),
            )
        )
        criteria = result.scalar_one_or_none()
        if not criteria:
            raise ValueError("评分标准不存在或无权限访问")
        return criteria

    async def _validate_job(self, job_id: Optional[UUID], user_id: UUID) -> None:
        if not job_id:
            return
        result = await self.db.execute(
            select(JobDescription.id).where(
                JobDescription.id == job_id,
                JobDescription.user_id == user_id,
                JobDescription.is_active.is_(True),
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("关联职位描述不存在或无权限访问")

    async def save_scoring_criteria(
        self, criteria_data: ScoringCriteriaCreate, user_id: UUID
    ) -> ScoringCriteriaResponse:
        payload = criteria_data.model_dump()
        await self._validate_job(payload.get("job_description_id"), user_id)
        payload["status"] = self._status_value(payload.get("status")) or "draft"
        payload["workflow_type"] = payload.get("workflow_type") or "scoring_criteria_generation"
        criteria = ScoringCriteria(
            **payload, user_id=user_id, created_by=user_id, updated_by=user_id
        )
        self.db.add(criteria)
        await self.db.commit()
        await self.db.refresh(criteria)
        return ScoringCriteriaResponse.model_validate(criteria)

    async def update_scoring_criteria(
        self, criteria_id: str, criteria_data: ScoringCriteriaUpdate, user_id: UUID
    ) -> ScoringCriteriaResponse:
        criteria = await self._owned_criteria(criteria_id, user_id)
        payload = criteria_data.model_dump(exclude_unset=True)
        if "job_description_id" in payload:
            await self._validate_job(payload["job_description_id"], user_id)
        if "status" in payload:
            payload["status"] = self._status_value(payload["status"])
        for key, value in payload.items():
            setattr(criteria, key, value)
        criteria.updated_by = user_id
        await self.db.commit()
        await self.db.refresh(criteria)
        return ScoringCriteriaResponse.model_validate(criteria)

    async def get_scoring_criteria(
        self, criteria_id: str, user_id: UUID
    ) -> ScoringCriteriaResponse:
        return ScoringCriteriaResponse.model_validate(
            await self._owned_criteria(criteria_id, user_id)
        )

    async def get_scoring_criteria_list(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 10,
        job_description_id: Optional[str] = None,
    ) -> ScoringCriteriaListResponse:
        filters = [
            ScoringCriteria.user_id == user_id,
            ScoringCriteria.is_active.is_(True),
        ]
        if job_description_id:
            try:
                filters.append(ScoringCriteria.job_description_id == UUID(str(job_description_id)))
            except ValueError as exc:
                raise ValueError("职位描述 ID 格式无效") from exc
        total = (
            await self.db.execute(select(func.count(ScoringCriteria.id)).where(*filters))
        ).scalar() or 0
        result = await self.db.execute(
            select(ScoringCriteria)
            .where(*filters)
            .order_by(ScoringCriteria.updated_at.desc(), ScoringCriteria.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = [ScoringCriteriaResponse.model_validate(item) for item in result.scalars().all()]
        return ScoringCriteriaListResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=math.ceil(total / size) if total else 0,
        )

    async def get_by_job_description(
        self, job_description_id: UUID, user_id: Optional[UUID] = None
    ) -> Optional[ScoringCriteriaResponse]:
        filters = [
            ScoringCriteria.job_description_id == job_description_id,
            ScoringCriteria.is_active.is_(True),
        ]
        if user_id:
            filters.append(ScoringCriteria.user_id == user_id)
        result = await self.db.execute(
            select(ScoringCriteria)
            .where(*filters)
            .order_by(ScoringCriteria.updated_at.desc())
            .limit(1)
        )
        criteria = result.scalar_one_or_none()
        return ScoringCriteriaResponse.model_validate(criteria) if criteria else None

    async def delete_scoring_criteria(
        self, criteria_id: str, user_id: UUID
    ) -> Dict[str, str]:
        criteria = await self._owned_criteria(criteria_id, user_id)
        criteria.is_active = False
        criteria.updated_by = user_id
        await self.db.commit()
        return {"message": "评分标准已删除", "id": str(criteria.id)}
