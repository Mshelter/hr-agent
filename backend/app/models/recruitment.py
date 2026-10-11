"""Local persistence models for the recruitment workflow."""

from sqlalchemy import Column, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class JobDescription(BaseModel):
    """A generated or manually maintained job description."""

    __tablename__ = "job_descriptions"

    title = Column(String(255), nullable=False, index=True)
    department = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    salary_range = Column(String(100), nullable=True)
    experience_level = Column(String(100), nullable=True)
    education = Column(String(100), nullable=True)
    job_type = Column(String(50), nullable=True)
    skills = Column(JSON, nullable=True)
    content = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    meta_data = Column(JSON, nullable=True)
    conversation_id = Column(String(255), nullable=True)
    workflow_type = Column(String(100), nullable=False, default="jd_generation")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)


class ScoringCriteria(BaseModel):
    """Resume scoring criteria associated with a job description."""

    __tablename__ = "scoring_criteria"

    title = Column(String(255), nullable=False, index=True)
    job_title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)
    criteria_data = Column(JSON, nullable=True)
    total_score = Column(String(10), nullable=True, default="100")
    scoring_dimensions = Column(JSON, nullable=True)
    status = Column(String(30), nullable=False, default="draft", index=True)
    meta_data = Column(JSON, nullable=True)
    conversation_id = Column(String(255), nullable=True)
    workflow_type = Column(String(100), nullable=False, default="scoring_criteria_generation")
    job_description_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_descriptions.id"),
        nullable=True,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)


class InterviewPlan(BaseModel):
    """An interview plan generated for a resume evaluation."""

    __tablename__ = "interview_plans"

    candidate_name = Column(String(100), nullable=False)
    candidate_position = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    resume_evaluation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("resume_evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
