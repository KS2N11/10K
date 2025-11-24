"""
Database package initialization.
Import all models to ensure they're registered with SQLAlchemy before create_all().
"""
from src.database.models import (
    Base,
    Company,
    Analysis,
    PainPoint,
    ProductMatch,
    Pitch,
    AnalysisJob
)

from src.database.scheduler_models import (
    SchedulerConfig,
    SchedulerRun,
    CompanyPriority,
    SchedulerMemory,
    SchedulerDecision
)

__all__ = [
    "Base",
    "Company",
    "Analysis",
    "PainPoint",
    "ProductMatch",
    "Pitch",
    "AnalysisJob",
    "SchedulerConfig",
    "SchedulerRun",
    "CompanyPriority",
    "SchedulerMemory",
    "SchedulerDecision",
]
