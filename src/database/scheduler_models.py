"""
Database models for autonomous scheduler.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, 
    JSON, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
import enum

from src.database.models import Base, MarketCap


class ScheduleStatus(str, enum.Enum):
    """Scheduler status."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"


class ScheduleDecisionReason(str, enum.Enum):
    """Reason for scheduling decision."""
    FIRST_TIME = "first_time"  # Never analyzed before
    STALE_DATA = "stale_data"  # Analysis too old
    CATALOG_UPDATED = "catalog_updated"  # Product catalog changed
    PERIODIC_REFRESH = "periodic_refresh"  # Regular refresh cycle
    HIGH_PRIORITY = "high_priority"  # High business value
    LLM_SUGGESTED = "llm_suggested"  # LLM agent recommendation


class SchedulerConfig(Base):
    """Configuration for autonomous scheduler."""
    __tablename__ = "scheduler_config"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Schedule settings
    cron_schedule = Column(String(100), nullable=False, default="0 2 * * *")  # Default: 2 AM daily
    is_active = Column(Boolean, default=False, nullable=False)
    continuous_mode = Column(Boolean, default=False, nullable=False)  # Run continuously (one after another)
    continuous_delay_minutes = Column(Integer, default=5)  # Delay between runs in continuous mode
    
    # Analysis strategy
    market_cap_priority = Column(JSON, default=["SMALL", "MID", "LARGE", "MEGA"])  # Priority order
    batch_size = Column(Integer, default=10)  # Companies per batch
    analysis_interval_days = Column(Integer, default=90)  # Re-analyze after N days
    
    # LLM decision making
    use_llm_agent = Column(Boolean, default=True)  # Let LLM decide which companies
    llm_temperature = Column(Float, default=0.3)  # Conservative decisions
    max_companies_per_run = Column(Integer, default=50)  # Max companies per scheduled run
    
    # Rate limiting
    min_time_between_runs_minutes = Column(Integer, default=60)  # Prevent too frequent runs
    max_concurrent_analyses = Column(Integer, default=5)  # Parallel analysis limit
    
    # Business rules
    prioritize_industries = Column(JSON, nullable=True)  # e.g., ["Technology", "Healthcare"]
    exclude_industries = Column(JSON, nullable=True)  # Industries to skip
    min_market_cap_value = Column(Float, nullable=True)  # Minimum market cap in $
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<SchedulerConfig(cron={self.cron_schedule}, active={self.is_active})>"


class SchedulerRun(Base):
    """Track each autonomous scheduler run."""
    __tablename__ = "scheduler_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    
    # Trigger info
    triggered_by = Column(String(50), default="scheduler")  # "scheduler", "manual", "api"
    trigger_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Decisions
    llm_reasoning = Column(Text, nullable=True)  # LLM's explanation for choices
    companies_selected = Column(JSON, nullable=False)  # List of {cik, name, reason}
    total_companies_considered = Column(Integer, default=0)
    
    # Execution
    job_id = Column(String(36), nullable=True)  # Reference to AnalysisJob
    status = Column(String(50), default="pending")  # "pending", "running", "completed", "failed"
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results
    companies_analyzed = Column(Integer, default=0)
    companies_skipped = Column(Integer, default=0)
    companies_failed = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)
    total_time_seconds = Column(Float, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_scheduler_run_time', 'trigger_time', 'status'),
    )
    
    def __repr__(self):
        return f"<SchedulerRun(run_id={self.run_id}, status={self.status}, companies={self.companies_analyzed})>"


class CompanyPriority(Base):
    """Track company priority for scheduling with memory."""
    __tablename__ = "company_priorities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cik = Column(String(10), unique=True, nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    
    # Priority calculation
    market_cap = Column(SQLEnum(MarketCap), nullable=True, index=True)
    industry = Column(String(255), nullable=True)
    sector = Column(String(100), nullable=True)
    
    # Scheduling memory
    times_analyzed = Column(Integer, default=0)  # How many times analyzed
    last_analyzed_at = Column(DateTime, nullable=True, index=True)
    next_scheduled_at = Column(DateTime, nullable=True, index=True)  # When to analyze next
    
    # Priority score (calculated by LLM)
    priority_score = Column(Float, default=0.0, index=True)  # 0-100
    priority_reason = Column(SQLEnum(ScheduleDecisionReason), nullable=True)
    
    # Business value indicators
    avg_product_match_score = Column(Float, nullable=True)  # Avg fit score from past analyses
    total_pain_points_found = Column(Integer, default=0)
    has_high_value_matches = Column(Boolean, default=False)  # Has matches > 80 score
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_priority_update = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_company_priority_scheduling', 'next_scheduled_at', 'priority_score'),
        Index('idx_company_priority_market_cap', 'market_cap', 'priority_score'),
    )
    
    def __repr__(self):
        return f"<CompanyPriority(cik={self.cik}, score={self.priority_score}, next={self.next_scheduled_at})>"


class SchedulerMemory(Base):
    """Persistent memory for scheduler decisions and learning."""
    __tablename__ = "scheduler_memory"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    memory_key = Column(String(255), unique=True, nullable=False, index=True)
    
    # Memory content
    memory_value = Column(JSON, nullable=False)
    memory_type = Column(String(50), nullable=False)  # "strategy", "learned_pattern", "blacklist"
    
    # Context
    description = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)  # How confident in this memory
    
    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    times_used = Column(Integer, default=0)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)  # Auto-forget after this time
    
    def __repr__(self):
        return f"<SchedulerMemory(key={self.memory_key}, type={self.memory_type})>"


class SchedulerJob(Base):
    """
    Persistent state for APScheduler jobs.
    
    This table stores the actual state of scheduler jobs, ensuring that
    next_run_time and other critical data persists across backend restarts.
    """
    __tablename__ = "scheduler_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), unique=True, nullable=False, index=True)  # APScheduler job ID
    
    # Job configuration
    job_name = Column(String(255), nullable=False)
    job_type = Column(String(50), nullable=False)  # "cron", "interval", "date"
    cron_schedule = Column(String(100), nullable=True)  # For cron jobs
    
    # Job state (critical for persistence)
    is_active = Column(Boolean, default=True, nullable=False)
    next_run_time = Column(DateTime, nullable=True, index=True)  # When job will run next
    last_run_time = Column(DateTime, nullable=True)  # When job last ran
    
    # Job execution tracking
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_scheduler_job_next_run', 'is_active', 'next_run_time'),
    )
    
    def __repr__(self):
        return f"<SchedulerJob(job_id={self.job_id}, next_run={self.next_run_time})>"


class SchedulerDecision(Base):
    """Log of each decision made by the scheduler LLM agent."""
    __tablename__ = "scheduler_decisions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(36), nullable=False, index=True)  # Reference to SchedulerRun
    
    # Decision details
    company_cik = Column(String(10), nullable=False, index=True)
    company_name = Column(String(255), nullable=False)
    
    # Decision
    decision = Column(String(20), nullable=False)  # "analyze", "skip", "defer"
    reason = Column(SQLEnum(ScheduleDecisionReason), nullable=True)
    reasoning = Column(Text, nullable=False)  # LLM explanation
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0
    
    # Context used
    market_cap = Column(SQLEnum(MarketCap), nullable=True)
    days_since_last_analysis = Column(Integer, nullable=True)
    previous_analysis_count = Column(Integer, default=0)
    previous_avg_match_score = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_scheduler_decision_company', 'company_cik', 'decision', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SchedulerDecision(company={self.company_name}, decision={self.decision})>"
