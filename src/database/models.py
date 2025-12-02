"""
Database models for 10K Insight Agent.
Uses SQLAlchemy ORM with PostgreSQL.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, 
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class MarketCap(str, enum.Enum):
    """Market capitalization categories."""
    SMALL = "SMALL"      # < $2B
    MID = "MID"          # $2B - $10B
    LARGE = "LARGE"      # $10B - $200B
    MEGA = "MEGA"        # > $200B


class AnalysisStatus(str, enum.Enum):
    """Analysis job status."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # Skipped due to cache


class Company(Base):
    """Company information from SEC."""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    cik = Column(String(10), unique=True, nullable=False, index=True)
    ticker = Column(String(10), nullable=True, index=True)
    industry = Column(String(255), nullable=True, index=True)
    sector = Column(String(100), nullable=True, index=True)
    market_cap = Column(SQLEnum(MarketCap), nullable=True, index=True)
    market_cap_value = Column(Integer, nullable=True)  # Actual $ value in dollars
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="company", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_company_search', 'name', 'ticker', 'cik'),
        Index('idx_company_filters', 'market_cap', 'industry', 'sector'),
    )
    
    def __repr__(self):
        return f"<Company(cik={self.cik}, name={self.name})>"


class Analysis(Base):
    """10-K analysis for a company."""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    
    # Filing info
    filing_date = Column(DateTime, nullable=False, index=True)
    accession_number = Column(String(20), nullable=False)
    filing_url = Column(String(500), nullable=True)
    filing_path = Column(String(500), nullable=True)  # Local storage path
    
    # Analysis status
    status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.QUEUED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Processing metrics
    time_taken_seconds = Column(Float, nullable=True)
    total_tokens_used = Column(Integer, default=0)
    embedding_tokens = Column(Integer, default=0)
    llm_tokens = Column(Integer, default=0)
    
    # Cache info
    used_cached_filing = Column(Boolean, default=False)
    used_cached_embeddings = Column(Boolean, default=False)
    
    # Product catalog version (to detect changes)
    catalog_hash = Column(String(64), nullable=True)  # SHA256 of products.json
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="analyses")
    pain_points = relationship("PainPoint", back_populates="analysis", cascade="all, delete-orphan")
    product_matches = relationship("ProductMatch", back_populates="analysis", cascade="all, delete-orphan")
    pitches = relationship("Pitch", back_populates="analysis", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_analysis_company_date', 'company_id', 'filing_date'),
        Index('idx_analysis_status', 'status', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Analysis(id={self.id}, company_id={self.company_id}, status={self.status})>"


class PainPoint(Base):
    """Identified pain point from 10-K."""
    __tablename__ = "pain_points"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    
    # Pain point details
    theme = Column(String(255), nullable=False, index=True)
    rationale = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    quotes = Column(JSON, nullable=True)  # List of supporting quotes
    
    # Categorization
    category = Column(String(100), nullable=True, index=True)  # e.g., "Financial", "Operational", "Regulatory"
    severity = Column(String(20), nullable=True)  # "High", "Medium", "Low"
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    analysis = relationship("Analysis", back_populates="pain_points")
    product_matches = relationship("ProductMatch", back_populates="pain_point", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_pain_category', 'category', 'confidence'),
    )
    
    def __repr__(self):
        return f"<PainPoint(id={self.id}, theme={self.theme}, confidence={self.confidence})>"


class ProductMatch(Base):
    """Product-to-pain match with scoring."""
    __tablename__ = "product_matches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    pain_point_id = Column(Integer, ForeignKey("pain_points.id"), nullable=False, index=True)
    
    # Product details
    product_id = Column(String(100), nullable=False, index=True)
    product_name = Column(String(255), nullable=False)
    product_category = Column(String(100), nullable=True)
    
    # Scoring
    fit_score = Column(Integer, nullable=False, index=True)  # 0-100
    why_fits = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)  # List of evidence points
    
    # Objections
    potential_objections = Column(JSON, nullable=True)  # List of objection dicts
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    analysis = relationship("Analysis", back_populates="product_matches")
    pain_point = relationship("PainPoint", back_populates="product_matches")
    pitches = relationship("Pitch", back_populates="product_match", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_match_score', 'fit_score', 'created_at'),
        Index('idx_match_product', 'product_id', 'fit_score'),
    )
    
    def __repr__(self):
        return f"<ProductMatch(id={self.id}, product_id={self.product_id}, score={self.fit_score})>"


class Pitch(Base):
    """Generated sales pitch."""
    __tablename__ = "pitches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    product_match_id = Column(Integer, ForeignKey("product_matches.id"), nullable=False, index=True)
    
    # Pitch content
    persona = Column(String(255), nullable=False)  # Target role (e.g., "CFO", "CTO")
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    key_quotes = Column(JSON, nullable=True)  # 10-K quotes used in pitch
    
    # Scoring (aggregated from match)
    overall_score = Column(Integer, nullable=False, index=True)  # Same as fit_score
    
    # Usage tracking
    sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    analysis = relationship("Analysis", back_populates="pitches")
    product_match = relationship("ProductMatch", back_populates="pitches")
    
    # Indexes
    __table_args__ = (
        Index('idx_pitch_score', 'overall_score', 'created_at'),
        Index('idx_pitch_persona', 'persona', 'overall_score'),
    )
    
    def __repr__(self):
        return f"<Pitch(id={self.id}, persona={self.persona}, score={self.overall_score})>"


class AnalysisJob(Base):
    """Batch analysis job tracking."""
    __tablename__ = "analysis_jobs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID
    
    # Job parameters
    filters = Column(JSON, nullable=True)  # Market cap, industry filters
    company_names = Column(JSON, nullable=True)  # Direct company list
    total_companies = Column(Integer, nullable=False)
    
    # Progress tracking
    completed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    current_company = Column(String(255), nullable=True)
    current_step = Column(String(100), nullable=True)
    estimated_time_remaining = Column(Float, nullable=True)  # seconds
    
    # Status
    status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.QUEUED, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Metrics
    total_time_seconds = Column(Float, nullable=True)
    total_tokens_used = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<AnalysisJob(job_id={self.job_id}, status={self.status}, progress={self.completed_count}/{self.total_companies})>"


class SystemMetrics(Base):
    """System-wide metrics snapshot."""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Aggregate stats
    total_companies_analyzed = Column(Integer, default=0)
    total_analyses_run = Column(Integer, default=0)
    total_pain_points_found = Column(Integer, default=0)
    total_pitches_generated = Column(Integer, default=0)
    
    # Performance metrics
    total_tokens_used = Column(Integer, default=0)
    total_processing_time_seconds = Column(Float, default=0)
    avg_time_per_analysis = Column(Float, default=0)
    
    # Time saved estimate (manual research vs automated)
    estimated_time_saved_hours = Column(Float, default=0)
    
    # Snapshot time
    snapshot_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def __repr__(self):
        return f"<SystemMetrics(snapshot_at={self.snapshot_at}, companies={self.total_companies_analyzed})>"
