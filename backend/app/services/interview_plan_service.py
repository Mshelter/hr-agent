"""Local PostgreSQL service for interview plans."""

import logging
import math
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select

from app.models.recruitment import InterviewPlan
from app.models.resume_evaluation import ResumeEvaluation
from app.schemas.interview_plan import (
    InterviewPlanCreate,
    InterviewPlanResponse,
    InterviewPlanUpdate,
)

logger = logging.getLogger(__name__)


class InterviewPlanService:
    def __init__(self, db):
        self.db = db

    async def _owned_plan(self, plan_id: UUID, user_id: UUID) -> InterviewPlan:
        result = await self.db.execute(
            select(InterviewPlan).where(
                InterviewPlan.id == plan_id,
                InterviewPlan.user_id == user_id,
                InterviewPlan.is_active.is_(True),
            )
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="面试方案未找到或无权限访问",
            )
        return plan

    async def create_interview_plan(
        self, user_id: UUID, plan_data: InterviewPlanCreate
    ) -> InterviewPlanResponse:
        result = await self.db.execute(
            select(ResumeEvaluation).where(
                ResumeEvaluation.id == plan_data.resume_evaluation_id,
                ResumeEvaluation.user_id == user_id,
                ResumeEvaluation.is_active.is_(True),
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="简历评价记录未找到或无权限访问",
            )
        plan = InterviewPlan(
            **plan_data.model_dump(),
            user_id=user_id,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        logger.info("成功创建本地面试方案: %s", plan.id)
        return InterviewPlanResponse.model_validate(plan)

    async def update_interview_plan(
        self, plan_id: UUID, user_id: UUID, plan_data: InterviewPlanUpdate
    ) -> InterviewPlanResponse:
        plan = await self._owned_plan(plan_id, user_id)
        for key, value in plan_data.model_dump(exclude_unset=True).items():
            setattr(plan, key, value)
        plan.updated_by = user_id
        await self.db.commit()
        await self.db.refresh(plan)
        return InterviewPlanResponse.model_validate(plan)

    async def get_interview_plan(
        self, plan_id: UUID, user_id: UUID
    ) -> InterviewPlanResponse:
        return InterviewPlanResponse.model_validate(await self._owned_plan(plan_id, user_id))

    async def list_interview_plans(
        self,
        user_id: UUID,
        page: int = 1,
        size: int = 10,
        resume_evaluation_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        filters = [InterviewPlan.user_id == user_id, InterviewPlan.is_active.is_(True)]
        if resume_evaluation_id:
            filters.append(InterviewPlan.resume_evaluation_id == resume_evaluation_id)
        total = (
            await self.db.execute(select(func.count(InterviewPlan.id)).where(*filters))
        ).scalar() or 0
        result = await self.db.execute(
            select(InterviewPlan)
            .where(*filters)
            .order_by(InterviewPlan.updated_at.desc(), InterviewPlan.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = [InterviewPlanResponse.model_validate(item) for item in result.scalars().all()]
        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": math.ceil(total / size) if total else 0,
        }

    async def delete_interview_plan(
        self, plan_id: UUID, user_id: UUID
    ) -> Dict[str, str]:
        plan = await self._owned_plan(plan_id, user_id)
        plan.is_active = False
        plan.updated_by = user_id
        await self.db.commit()
        return {"message": "面试方案已删除", "id": str(plan.id)}

    async def delete_by_evaluation(self, evaluation_id: UUID, user_id: UUID) -> int:
        result = await self.db.execute(
            select(InterviewPlan).where(
                InterviewPlan.resume_evaluation_id == evaluation_id,
                InterviewPlan.user_id == user_id,
            )
        )
        plans = result.scalars().all()
        for plan in plans:
            await self.db.delete(plan)
        await self.db.flush()
        return len(plans)
