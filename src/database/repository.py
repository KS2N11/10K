"""
Database repository layer for CRUD operations.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session

from src.database.models import (
    Company, Analysis, PainPoint, ProductMatch, Pitch,
    AnalysisJob, SystemMetrics, MarketCap, AnalysisStatus
)


class CompanyRepository:
    """Repository for Company operations."""
    
    @staticmethod
    def create(db: Session, cik: str, name: str, **kwargs) -> Company:
        """Create a new company."""
        company = Company(cik=cik, name=name, **kwargs)
        db.add(company)
        db.commit()
        db.refresh(company)
        return company
    
    @staticmethod
    def get_by_cik(db: Session, cik: str) -> Optional[Company]:
        """Get company by CIK."""
        return db.query(Company).filter(Company.cik == cik).first()
    
    @staticmethod
    def get_or_create(db: Session, cik: str, name: str, **kwargs) -> Company:
        """Get existing company or create new one."""
        company = CompanyRepository.get_by_cik(db, cik)
        if not company:
            company = CompanyRepository.create(db, cik, name, **kwargs)
        return company
    
    @staticmethod
    def search(
        db: Session,
        query: Optional[str] = None,
        market_cap: Optional[List[MarketCap]] = None,
        industry: Optional[List[str]] = None,
        sector: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Company]:
        """Search companies with filters."""
        q = db.query(Company)
        
        # Text search
        if query:
            search_filter = or_(
                Company.name.ilike(f"%{query}%"),
                Company.ticker.ilike(f"%{query}%"),
                Company.cik.ilike(f"%{query}%")
            )
            q = q.filter(search_filter)
        
        # Market cap filter
        if market_cap:
            q = q.filter(Company.market_cap.in_(market_cap))
        
        # Industry filter
        if industry:
            q = q.filter(Company.industry.in_(industry))
        
        # Sector filter
        if sector:
            q = q.filter(Company.sector.in_(sector))
        
        return q.order_by(Company.name).limit(limit).offset(offset).all()
    
    @staticmethod
    def get_all_analyzed(db: Session) -> List[Company]:
        """Get all companies with at least one completed analysis."""
        return db.query(Company).join(Analysis).filter(
            Analysis.status == AnalysisStatus.COMPLETED
        ).distinct().all()


class AnalysisRepository:
    """Repository for Analysis operations."""
    
    @staticmethod
    def create(db: Session, company_id: int, **kwargs) -> Analysis:
        """Create a new analysis."""
        analysis = Analysis(company_id=company_id, **kwargs)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis
    
    @staticmethod
    def get_latest_for_company(db: Session, company_id: int) -> Optional[Analysis]:
        """Get most recent completed analysis for a company."""
        return db.query(Analysis).filter(
            and_(
                Analysis.company_id == company_id,
                Analysis.status == AnalysisStatus.COMPLETED
            )
        ).order_by(desc(Analysis.filing_date)).first()
    
    @staticmethod
    def should_reanalyze(
        db: Session,
        company_id: int,
        current_filing_date: datetime,
        current_catalog_hash: str
    ) -> bool:
        """
        Determine if company needs re-analysis.
        Returns True if:
        - No previous analysis exists
        - Newer 10-K filing available
        - Product catalog has changed
        """
        latest = AnalysisRepository.get_latest_for_company(db, company_id)
        
        if not latest:
            return True  # Never analyzed
        
        if latest.filing_date < current_filing_date:
            return True  # Newer filing available
        
        if latest.catalog_hash != current_catalog_hash:
            return True  # Catalog changed
        
        return False  # Use cached analysis
    
    @staticmethod
    def update_status(
        db: Session,
        analysis_id: int,
        status: AnalysisStatus,
        **kwargs
    ) -> Analysis:
        """Update analysis status and metrics."""
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if analysis:
            analysis.status = status
            analysis.updated_at = datetime.utcnow()
            
            if status == AnalysisStatus.IN_PROGRESS and not analysis.started_at:
                analysis.started_at = datetime.utcnow()
            elif status == AnalysisStatus.COMPLETED:
                analysis.completed_at = datetime.utcnow()
                if analysis.started_at:
                    analysis.time_taken_seconds = (
                        analysis.completed_at - analysis.started_at
                    ).total_seconds()
            
            for key, value in kwargs.items():
                setattr(analysis, key, value)
            
            db.commit()
            db.refresh(analysis)
        return analysis
    
    @staticmethod
    def get_all_completed(
        db: Session,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Analysis]:
        """Get all completed analyses with optional filters."""
        q = db.query(Analysis).filter(Analysis.status == AnalysisStatus.COMPLETED)
        
        if filters:
            # Add filter logic as needed
            pass
        
        return q.order_by(desc(Analysis.completed_at)).limit(limit).offset(offset).all()


class PainPointRepository:
    """Repository for PainPoint operations."""
    
    @staticmethod
    def create_bulk(db: Session, analysis_id: int, pain_points: List[Dict[str, Any]]) -> List[PainPoint]:
        """Create multiple pain points for an analysis."""
        pain_objs = []
        for pain_data in pain_points:
            pain = PainPoint(analysis_id=analysis_id, **pain_data)
            db.add(pain)
            pain_objs.append(pain)
        
        db.commit()
        for pain in pain_objs:
            db.refresh(pain)
        
        return pain_objs
    
    @staticmethod
    def get_by_analysis(db: Session, analysis_id: int) -> List[PainPoint]:
        """Get all pain points for an analysis."""
        return db.query(PainPoint).filter(
            PainPoint.analysis_id == analysis_id
        ).order_by(desc(PainPoint.confidence)).all()


class ProductMatchRepository:
    """Repository for ProductMatch operations."""
    
    @staticmethod
    def create_bulk(
        db: Session,
        analysis_id: int,
        matches: List[Dict[str, Any]]
    ) -> List[ProductMatch]:
        """Create multiple product matches for an analysis."""
        match_objs = []
        for match_data in matches:
            match = ProductMatch(analysis_id=analysis_id, **match_data)
            db.add(match)
            match_objs.append(match)
        
        db.commit()
        for match in match_objs:
            db.refresh(match)
        
        return match_objs
    
    @staticmethod
    def get_top_matches(
        db: Session,
        min_score: int = 70,
        limit: int = 50
    ) -> List[ProductMatch]:
        """Get top-scoring product matches across all analyses."""
        return db.query(ProductMatch).filter(
            ProductMatch.fit_score >= min_score
        ).order_by(desc(ProductMatch.fit_score)).limit(limit).all()
    
    @staticmethod
    def get_by_analysis(db: Session, analysis_id: int) -> List[ProductMatch]:
        """Get all product matches for an analysis."""
        return db.query(ProductMatch).filter(
            ProductMatch.analysis_id == analysis_id
        ).order_by(desc(ProductMatch.fit_score)).all()


class PitchRepository:
    """Repository for Pitch operations."""
    
    @staticmethod
    def create_bulk(
        db: Session,
        pitches: List[Dict[str, Any]]
    ) -> List[Pitch]:
        """Create multiple pitches."""
        pitch_objs = []
        for pitch_data in pitches:
            pitch = Pitch(**pitch_data)
            db.add(pitch)
            pitch_objs.append(pitch)
        
        db.commit()
        for pitch in pitch_objs:
            db.refresh(pitch)
        
        return pitch_objs
    
    @staticmethod
    def get_top_pitches(
        db: Session,
        min_score: int = 75,
        limit: int = 50
    ) -> List[Pitch]:
        """Get top-scoring pitches across all analyses."""
        return db.query(Pitch).filter(
            Pitch.overall_score >= min_score
        ).order_by(desc(Pitch.overall_score), desc(Pitch.created_at)).limit(limit).all()
    
    @staticmethod
    def get_by_persona(db: Session, persona: str, limit: int = 20) -> List[Pitch]:
        """Get pitches for a specific persona."""
        return db.query(Pitch).filter(
            Pitch.persona == persona
        ).order_by(desc(Pitch.overall_score)).limit(limit).all()


class AnalysisJobRepository:
    """Repository for AnalysisJob operations."""
    
    @staticmethod
    def create(db: Session, job_id: str, **kwargs) -> AnalysisJob:
        """Create a new analysis job."""
        job = AnalysisJob(job_id=job_id, **kwargs)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    
    @staticmethod
    def get_by_job_id(db: Session, job_id: str) -> Optional[AnalysisJob]:
        """Get job by ID."""
        return db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
    
    @staticmethod
    def update_progress(
        db: Session,
        job_id: str,
        **kwargs
    ) -> Optional[AnalysisJob]:
        """Update job progress."""
        job = AnalysisJobRepository.get_by_job_id(db, job_id)
        if job:
            for key, value in kwargs.items():
                setattr(job, key, value)
            job.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(job)
        return job


class MetricsRepository:
    """Repository for system metrics."""
    
    @staticmethod
    def get_current_metrics(db: Session) -> Dict[str, Any]:
        """Calculate current system metrics."""
        total_companies = db.query(func.count(Company.id)).scalar() or 0
        total_analyses = db.query(func.count(Analysis.id)).filter(
            Analysis.status == AnalysisStatus.COMPLETED
        ).scalar() or 0
        total_pains = db.query(func.count(PainPoint.id)).scalar() or 0
        total_pitches = db.query(func.count(Pitch.id)).scalar() or 0
        
        # Aggregate metrics
        metrics = db.query(
            func.sum(Analysis.total_tokens_used).label('total_tokens'),
            func.sum(Analysis.time_taken_seconds).label('total_time'),
            func.avg(Analysis.time_taken_seconds).label('avg_time')
        ).filter(Analysis.status == AnalysisStatus.COMPLETED).first()
        
        total_tokens = metrics.total_tokens or 0
        total_time = metrics.total_time or 0
        avg_time = metrics.avg_time or 0
        
        # Estimate time saved (assume 2 hours manual research per company)
        time_saved_hours = total_analyses * 2
        
        return {
            "total_companies_analyzed": total_companies,
            "total_analyses_run": total_analyses,
            "total_pain_points_found": total_pains,
            "total_pitches_generated": total_pitches,
            "total_tokens_used": int(total_tokens),
            "total_processing_time_seconds": total_time,
            "avg_time_per_analysis": avg_time,
            "estimated_time_saved_hours": time_saved_hours
        }
    
    @staticmethod
    def save_snapshot(db: Session) -> SystemMetrics:
        """Save current metrics snapshot."""
        current = MetricsRepository.get_current_metrics(db)
        snapshot = SystemMetrics(**current)
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
    
    @staticmethod
    def get_trend(db: Session, days: int = 30) -> List[SystemMetrics]:
        """Get metrics trend for last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        return db.query(SystemMetrics).filter(
            SystemMetrics.snapshot_at >= cutoff
        ).order_by(SystemMetrics.snapshot_at).all()
