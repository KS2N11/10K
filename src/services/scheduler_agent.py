"""
LLM-powered agent for intelligent scheduling decisions.
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from src.database.models import MarketCap, AnalysisStatus
from src.database.scheduler_models import (
    ScheduleDecisionReason, CompanyPriority, SchedulerMemory, SchedulerDecision
)
from src.database.repository import CompanyRepository, AnalysisRepository
from src.utils.multi_llm import MultiProviderLLM
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SchedulerAgent:
    """LLM-powered agent that makes intelligent scheduling decisions."""
    
    def __init__(self, llm_manager: MultiProviderLLM, config: Dict[str, Any]):
        """
        Initialize scheduler agent.
        
        Args:
            llm_manager: Multi-provider LLM manager
            config: Configuration dict with scheduler settings
        """
        self.llm = llm_manager
        self.config = config
        self.temperature = config.get("llm_temperature", 0.3)
    
    async def decide_companies_to_analyze(
        self,
        run_id: str,
        market_cap_priority: List[str],
        batch_size: int,
        analysis_interval_days: int,
        prioritize_industries: Optional[List[str]] = None,
        exclude_industries: Optional[List[str]] = None,
        max_companies: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Use LLM agent to decide which companies to analyze.
        
        Args:
            run_id: Scheduler run ID
            market_cap_priority: Priority order for market caps
            batch_size: Companies per batch
            analysis_interval_days: Re-analyze after N days
            prioritize_industries: Industries to prioritize
            exclude_industries: Industries to exclude
            max_companies: Maximum companies to return
        
        Returns:
            List of company dicts with {cik, name, ticker, reason, confidence}
        """
        from src.database.database import get_db
        
        logger.info(f"🤖 Scheduler agent deciding companies to analyze...")
        
        # Get candidate companies from SEC database
        candidates = await self._get_candidate_companies(
            market_cap_priority,
            analysis_interval_days,
            prioritize_industries,
            exclude_industries,
            max_companies * 2  # Get more candidates than needed
        )
        
        logger.info(f"Found {len(candidates)} candidate companies")
        
        if not candidates:
            logger.warning("No candidate companies found")
            return []
        
        # Get historical context
        with get_db() as db:
            memory_context = self._get_memory_context(db)
        
        # Build prompt for LLM
        prompt = self._build_decision_prompt(
            candidates,
            memory_context,
            market_cap_priority,
            batch_size,
            analysis_interval_days,
            prioritize_industries,
            max_companies
        )
        
        # Get LLM decision
        logger.info(f"Asking LLM to select from {len(candidates)} candidates...")
        response = await self.llm.ainvoke(
            prompt,
            temperature=self.temperature,
            max_tokens=2000
        )
        
        # Parse LLM response
        decisions = self._parse_llm_decisions(response, candidates)
        
        # Log decisions to database
        with get_db() as db:
            for decision in decisions:
                self._log_decision(
                    db,
                    run_id,
                    decision["cik"],
                    decision["name"],
                    "analyze",
                    decision["reason"],
                    decision["reasoning"],
                    decision.get("confidence", 0.8),
                    decision.get("market_cap"),
                    decision.get("days_since_last_analysis"),
                    decision.get("previous_analysis_count", 0),
                    decision.get("previous_avg_match_score")
                )
            
            # Log skipped companies
            selected_ciks = {d["cik"] for d in decisions}
            for candidate in candidates:
                if candidate["cik"] not in selected_ciks:
                    self._log_decision(
                        db,
                        run_id,
                        candidate["cik"],
                        candidate["name"],
                        "skip",
                        ScheduleDecisionReason.PERIODIC_REFRESH,
                        "Not selected by LLM in this batch",
                        0.5,
                        candidate.get("market_cap"),
                        candidate.get("days_since_last_analysis"),
                        candidate.get("previous_analysis_count", 0),
                        candidate.get("previous_avg_match_score")
                    )
        
        # Update memory with new learnings
        with get_db() as db:
            self._update_memory(db, decisions, memory_context)
        
        logger.info(f"✅ LLM selected {len(decisions)} companies to analyze")
        
        return decisions
    
    async def _get_candidate_companies(
        self,
        market_cap_priority: List[str],
        analysis_interval_days: int,
        prioritize_industries: Optional[List[str]],
        exclude_industries: Optional[List[str]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get candidate companies for analysis based on priority rules."""
        from src.utils.sec_filter import SECCompanyFilter
        from src.database.database import get_db
        
        candidates = []
        
        # Market cap thresholds configuration
        # If strict_small_cap_threshold is set in config, use strict filtering
        # Otherwise, use tiered approach: $2B -> $4B -> $10B -> $50B -> unlimited
        strict_threshold = self.config.get("strict_small_cap_threshold")
        use_strict_mode = strict_threshold is not None
        
        if use_strict_mode:
            small_cap_threshold = strict_threshold
            logger.info(f"Using STRICT mode: Only companies < ${small_cap_threshold:,}")
        else:
            # Tiered thresholds: gradually expand if not enough candidates
            tiered_thresholds = [
                2_000_000_000,   # $2B - Small cap
                4_000_000_000,   # $4B - Small-to-Mid cap
                10_000_000_000,  # $10B - Mid cap
                50_000_000_000,  # $50B - Large cap
                None             # Unlimited - all companies
            ]
            logger.info(f"Using TIERED mode: $2B -> $4B -> $10B -> $50B -> unlimited")
            logger.info(f"Using TIERED mode: $2B -> $4B -> $10B -> $50B -> unlimited")
        
        # Get companies for each market cap tier in priority order
        sec_filter = SECCompanyFilter(self.config.get("sec_user_agent"))
        
        # Collect ALL potential candidates first (before filtering by market cap)
        all_potential_candidates = []
        
        for market_cap in market_cap_priority:
            logger.info(f"Fetching {market_cap} cap companies...")
            
            # Fetch companies from SEC
            companies = await sec_filter.search_companies(
                market_cap=[market_cap],
                industry=prioritize_industries,
                limit=limit // len(market_cap_priority),
                use_realtime_lookup=False  # Use static mapping for reliability
            )
            
            # Handle None or empty results
            if companies is None:
                logger.warning(f"search_companies returned None for {market_cap} cap")
                companies = []
            
            # Enrich with database history
            for company in companies:
                cik = company.get("cik")
                
                with get_db() as db:
                    # Check if company exists in database
                    db_company = CompanyRepository.get_by_cik(db, cik)
                    
                    if not db_company:
                        # Company not in database yet, skip it
                        logger.debug(f"Skipping {company.get('name')} - not in database")
                        continue
                    
                    # Get latest analysis
                    latest_analysis = None
                    days_since = None
                    if db_company:
                        latest_analysis = AnalysisRepository.get_latest_for_company(db, db_company.id)
                        if latest_analysis and latest_analysis.completed_at:
                            days_since = (datetime.utcnow() - latest_analysis.completed_at).days
                    
                    # Get priority record
                    priority = db.query(CompanyPriority).filter(
                        CompanyPriority.cik == cik
                    ).first()
                    
                    # Extract priority data before leaving session
                    priority_data = {
                        'times_analyzed': priority.times_analyzed if priority else 0,
                        'avg_product_match_score': priority.avg_product_match_score if priority else None,
                        'has_high_value_matches': priority.has_high_value_matches if priority else False,
                        'priority_score': priority.priority_score if priority else 50.0
                    }
                    
                    # Extract market cap value before leaving session
                    market_cap_value = db_company.market_cap_value if db_company else None
                
                # Determine if company should be considered
                should_consider = False
                reason = None

                # Never analyzed before → include
                if not latest_analysis:
                    should_consider = True
                    reason = ScheduleDecisionReason.FIRST_TIME
                # Analyzed before but stale beyond interval → include
                elif days_since is not None and days_since >= analysis_interval_days:
                    should_consider = True
                    reason = ScheduleDecisionReason.STALE_DATA
                
                if should_consider:
                    # Check exclusions
                    if exclude_industries and company.get("industry") in exclude_industries:
                        continue
                    
                    all_potential_candidates.append({
                        "cik": cik,
                        "name": company.get("name"),
                        "ticker": company.get("ticker"),
                        "market_cap": market_cap,
                        "market_cap_value": market_cap_value,
                        "industry": company.get("industry"),
                        "sector": company.get("sector"),
                        "days_since_last_analysis": days_since,
                        "previous_analysis_count": priority_data['times_analyzed'],
                        "previous_avg_match_score": priority_data['avg_product_match_score'],
                        "has_high_value_matches": priority_data['has_high_value_matches'],
                        "reason": reason,
                        "priority_score": priority_data['priority_score']
                    })
            
            if len(all_potential_candidates) >= limit * 2:
                break
        
        logger.info(f"Found {len(all_potential_candidates)} total potential candidates")
        
        # Now apply market cap filtering based on mode
        if use_strict_mode:
            # STRICT MODE: Only include companies < threshold, exclude unknowns
            candidates = [
                c for c in all_potential_candidates
                if c["market_cap_value"] is not None and c["market_cap_value"] < small_cap_threshold
            ]
            logger.info(f"STRICT mode: Filtered to {len(candidates)} companies < ${small_cap_threshold:,}")
            
        else:
            # TIERED MODE: Try each threshold tier until we have enough candidates
            for tier_threshold in tiered_thresholds:
                if tier_threshold is None:
                    # Final tier: include all companies with known market cap
                    candidates = [
                        c for c in all_potential_candidates
                        if c["market_cap_value"] is not None
                    ]
                    logger.info(f"TIERED mode (unlimited): Found {len(candidates)} companies with known market cap")
                else:
                    # Try this threshold tier
                    candidates = [
                        c for c in all_potential_candidates
                        if c["market_cap_value"] is not None and c["market_cap_value"] < tier_threshold
                    ]
                    logger.info(f"TIERED mode (< ${tier_threshold:,}): Found {len(candidates)} candidates")
                
                # If we have enough candidates, stop expanding
                if len(candidates) >= limit:
                    logger.info(f"✓ Sufficient candidates found at threshold: ${tier_threshold:,}" if tier_threshold else "✓ Sufficient candidates found (unlimited)")
                    break
        
        if not candidates:
            logger.warning("No candidates found even after tiered expansion - returning empty list")
        if not candidates:
            logger.warning("No candidates found even after tiered expansion - returning empty list")
        
        # Sort by market cap value (smaller first), then by priority
        def sort_key(c):
            # Prioritize by actual market cap value (smaller first)
            mc_value = c.get("market_cap_value", 999_999_999_999)
            priority_score = c.get("priority_score", 50.0)
            has_matches = 1 if c.get("has_high_value_matches") else 0
            days_since = c.get("days_since_last_analysis", 0) or 0
            
            return (
                mc_value,            # Smallest market cap FIRST
                -priority_score,     # Then by priority score
                -has_matches,        # Then high value matches
                -days_since          # Finally by staleness
            )
        
        candidates.sort(key=sort_key)
        
        logger.info(f"Final candidate list: {len(candidates)} companies sorted by market cap (smallest first)")
        
        return candidates[:limit]
    
    def _get_memory_context(self, db: Session) -> Dict[str, Any]:
        """Get relevant memory context for decision making."""
        memory_records = db.query(SchedulerMemory).filter(
            SchedulerMemory.memory_type.in_(["strategy", "learned_pattern"])
        ).order_by(SchedulerMemory.times_used.desc()).limit(10).all()
        
        context = {
            "strategies": [],
            "learned_patterns": []
        }
        
        for record in memory_records:
            if record.memory_type == "strategy":
                context["strategies"].append({
                    "key": record.memory_key,
                    "value": record.memory_value,
                    "description": record.description,
                    "confidence": record.confidence,
                    "times_used": record.times_used
                })
            elif record.memory_type == "learned_pattern":
                context["learned_patterns"].append({
                    "key": record.memory_key,
                    "value": record.memory_value,
                    "description": record.description,
                    "confidence": record.confidence
                })
        
        return context
    
    def _build_decision_prompt(
        self,
        candidates: List[Dict[str, Any]],
        memory_context: Dict[str, Any],
        market_cap_priority: List[str],
        batch_size: int,
        analysis_interval_days: int,
        prioritize_industries: Optional[List[str]],
        max_companies: int
    ) -> str:
        """Build prompt for LLM to make scheduling decisions."""
        
        # Limit candidates in prompt to prevent token overflow
        candidates_summary = candidates[:50]  # Max 50 for prompt
        
        prompt = f"""You are an intelligent scheduler agent for a 10-K analysis system. Your job is to select which companies to analyze next.

**GOAL**: Select up to {max_companies} companies to analyze, prioritizing by:
1. Market cap priority: {', '.join(market_cap_priority)} (in that order - SMALL caps first!)
2. Business value (companies with high-scoring product matches in past)
3. Data freshness (companies not analyzed recently or never analyzed)
4. Industry relevance {f"(prioritize: {', '.join(prioritize_industries)})" if prioritize_industries else ""}

**MEMORY CONTEXT**:
Past successful strategies:
{json.dumps(memory_context.get("strategies", []), indent=2)}

Learned patterns:
{json.dumps(memory_context.get("learned_patterns", []), indent=2)}

**ANALYSIS RULES**:
- Re-analyze companies after {analysis_interval_days} days
- Focus on SMALL and MID cap companies first (they need more help!)
- LARGE and MEGA cap companies should be analyzed less frequently
- Prioritize companies that had high-value matches before (avg_match_score > 75)
- First-time companies are interesting (never analyzed before)

**CANDIDATE COMPANIES** ({len(candidates_summary)} shown):
{json.dumps(candidates_summary, indent=2)}

**YOUR TASK**:
Select up to {max_companies} companies to analyze. For each company, explain:
1. Why you selected them (market cap tier, business value, freshness, etc.)
2. Expected value (why this company matters)
3. Confidence (0.0 - 1.0)

**OUTPUT FORMAT** (JSON only, no explanation):
{{
    "reasoning": "Overall strategy explanation (2-3 sentences)",
    "selected_companies": [
        {{
            "cik": "0001234567",
            "name": "Company Name",
            "reason": "first_time" | "stale_data" | "high_priority" | "periodic_refresh",
            "reasoning": "Detailed explanation (1-2 sentences)",
            "confidence": 0.85,
            "expected_value": "Why this company matters (1 sentence)"
        }}
    ]
}}

Focus on SMALL and MID cap companies first! They need the most analysis help.
Return valid JSON only.
"""
        
        return prompt
    
    def _parse_llm_decisions(
        self,
        llm_response: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse LLM response and match with candidate companies."""
        try:
            # Try multiple JSON extraction methods
            response_text = llm_response.strip()
            
            # Method 1: Find JSON between code blocks
            if "```" in response_text:
                for block in response_text.split("```"):
                    if block.strip().startswith(("{", "[")):
                        try:
                            response_data = json.loads(block.strip())
                            break
                        except:
                            continue
            
            # Method 2: Find first { to last } in the entire text
            if "response_data" not in locals():
                try:
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    if start >= 0 and end > start:
                        response_data = json.loads(response_text[start:end])
                except:
                    pass
            
            # Method 3: Try the whole response as JSON
            if "response_data" not in locals():
                try:
                    response_data = json.loads(response_text)
                except:
                    logger.error("Could not parse JSON from LLM response")
                    raise ValueError("Invalid JSON format")
            
            decisions = []
            candidate_lookup = {c["cik"]: c for c in candidates}
            
            # Validate expected structure
            if not isinstance(response_data, dict) or "selected_companies" not in response_data:
                raise ValueError("Response missing 'selected_companies' array")
            
            selected_companies = response_data.get("selected_companies", [])
            if not isinstance(selected_companies, list):
                raise ValueError("'selected_companies' must be an array")
            
            for selected in selected_companies:
                if not isinstance(selected, dict):
                    continue
                    
                cik = selected.get("cik")
                if not cik or cik not in candidate_lookup:
                    continue
                    
                candidate = candidate_lookup[cik]
                
                # Validate and clean reason
                reason = selected.get("reason", "periodic_refresh")
                try:
                    reason = ScheduleDecisionReason(reason)
                except ValueError:
                    reason = ScheduleDecisionReason.PERIODIC_REFRESH
                
                decisions.append({
                    "cik": cik,
                    "name": selected.get("name", candidate["name"]),
                    "ticker": candidate.get("ticker"),
                    "market_cap": candidate.get("market_cap"),
                    "industry": candidate.get("industry"),
                    "reason": reason,
                    "reasoning": selected.get("reasoning", "Selected by LLM").strip() or "Selected by LLM",
                    "confidence": min(1.0, max(0.0, float(selected.get("confidence", 0.8)))),
                    "expected_value": selected.get("expected_value", "").strip(),
                    "days_since_last_analysis": candidate.get("days_since_last_analysis"),
                    "previous_analysis_count": candidate.get("previous_analysis_count", 0),
                    "previous_avg_match_score": candidate.get("previous_avg_match_score")
                })
            
            if decisions:
                logger.info(f"✅ Successfully parsed {len(decisions)} decisions from LLM response")
                return decisions
        
        except Exception as e:
            logger.error(f"Error parsing LLM decisions: {e}")
            logger.error(f"LLM response: {llm_response}")
            
            # Final fallback: smart rule-based selection
            logger.warning("Using smart rule-based selection")
            return self._smart_fallback_selection(candidates)
    
    def _smart_fallback_selection(
        self,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Intelligent rule-based selection that strictly enforces market cap priority."""
        decisions = []
        candidates_by_cap = {}
        
        # Group by market cap
        for candidate in candidates:
            cap = candidate.get("market_cap")
            if cap:
                if cap not in candidates_by_cap:
                    candidates_by_cap[cap] = []
                candidates_by_cap[cap].append(candidate)
        
        # Select companies in strict market cap priority order
        for market_cap in self.config.get("market_cap_priority", ["SMALL", "MID", "LARGE", "MEGA"]):
            cap_candidates = candidates_by_cap.get(market_cap, [])
            
            # Sort by priority score and staleness
            cap_candidates.sort(key=lambda x: (
                -(x.get("priority_score", 50.0)),
                -(x.get("days_since_last_analysis", 0) or 0)
            ))
            
            # Take up to 5 from each cap tier
            for candidate in cap_candidates[:5]:
                decisions.append({
                    "cik": candidate["cik"],
                    "name": candidate["name"],
                    "ticker": candidate.get("ticker"),
                    "market_cap": candidate.get("market_cap"),
                    "industry": candidate.get("industry"),
                    "reason": candidate.get("reason", ScheduleDecisionReason.PERIODIC_REFRESH),
                    "reasoning": f"Selected by priority in {market_cap} cap tier",
                    "confidence": 0.7,
                    "expected_value": "Market cap prioritization (SMALL->MEGA)",
                    "days_since_last_analysis": candidate.get("days_since_last_analysis"),
                    "previous_analysis_count": candidate.get("previous_analysis_count", 0),
                    "previous_avg_match_score": candidate.get("previous_avg_match_score")
                })
            
            if len(decisions) >= 10:
                break
        
        return decisions
    
    def _log_decision(
        self,
        db: Session,
        run_id: str,
        cik: str,
        name: str,
        decision: str,
        reason: ScheduleDecisionReason,
        reasoning: str,
        confidence: float,
        market_cap: Optional[str],
        days_since: Optional[int],
        prev_count: int,
        prev_score: Optional[float]
    ):
        """Log a scheduling decision to database."""
        decision_record = SchedulerDecision(
            run_id=run_id,
            company_cik=cik,
            company_name=name,
            decision=decision,
            reason=reason,
            reasoning=reasoning,
            confidence=confidence,
            market_cap=MarketCap(market_cap) if market_cap else None,
            days_since_last_analysis=days_since,
            previous_analysis_count=prev_count,
            previous_avg_match_score=prev_score
        )
        db.add(decision_record)
        db.commit()
    
    def _update_memory(
        self,
        db: Session,
        decisions: List[Dict[str, Any]],
        memory_context: Dict[str, Any]
    ):
        """Update scheduler memory with new learnings."""
        # Learn from this batch
        market_cap_distribution = {}
        for decision in decisions:
            market_cap = decision.get("market_cap")
            if market_cap:
                market_cap_distribution[market_cap] = market_cap_distribution.get(market_cap, 0) + 1
        
        # Save learned pattern
        memory_key = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
        memory_record = SchedulerMemory(
            memory_key=memory_key,
            memory_type="learned_pattern",
            memory_value={
                "market_cap_distribution": market_cap_distribution,
                "total_selected": len(decisions),
                "avg_confidence": sum(d.get("confidence", 0) for d in decisions) / len(decisions) if decisions else 0
            },
            description=f"Batch selection on {datetime.utcnow().isoformat()}",
            confidence=0.8
        )
        db.add(memory_record)
        db.commit()
        
        logger.info(f"💾 Updated scheduler memory with new learning")
    
    async def update_company_priorities(
        self,
        analysis_interval_days: int = 90
    ):
        """Update company priority scores based on recent analyses."""
        from src.database.models import Company, Analysis, ProductMatch
        from src.database.database import get_db
        
        logger.info("Updating company priorities...")
        
        with get_db() as db:
            # Get all companies with at least one analysis
            companies = db.query(Company).join(Analysis).group_by(Company.id).all()
            
            for company in companies:
                # Get latest analysis
                latest_analysis = AnalysisRepository.get_latest_for_company(db, company.id)
                
                if not latest_analysis:
                    continue
                
                # Calculate metrics
                analyses = db.query(Analysis).filter(
                    Analysis.company_id == company.id,
                    Analysis.status == AnalysisStatus.COMPLETED
                ).all()
                
                times_analyzed = len(analyses)
                last_analyzed_at = latest_analysis.completed_at
                
                # Calculate average match score
                all_matches = db.query(ProductMatch).join(Analysis).filter(
                    Analysis.company_id == company.id
                ).all()
                
                avg_score = sum(m.fit_score for m in all_matches) / len(all_matches) if all_matches else 0
                has_high_value = any(m.fit_score >= 80 for m in all_matches)
                total_pains = sum(len(a.pain_points) for a in analyses)
                
                # Calculate next scheduled time
                next_scheduled = last_analyzed_at + timedelta(days=analysis_interval_days) if last_analyzed_at else datetime.utcnow()
                
                # Calculate priority score (0-100)
                priority_score = 50.0  # Base score
                
                # Boost for high value matches
                if has_high_value:
                    priority_score += 25
                elif avg_score > 70:
                    priority_score += 15
                
                # Boost for more pain points found
                if total_pains > 10:
                    priority_score += 10
                
                # Reduce for frequent analyses (don't analyze too often)
                if times_analyzed > 3:
                    priority_score -= 10
                
                # Determine reason
                days_since = (datetime.utcnow() - last_analyzed_at).days if last_analyzed_at else 999
                if days_since >= analysis_interval_days:
                    reason = ScheduleDecisionReason.STALE_DATA
                elif has_high_value:
                    reason = ScheduleDecisionReason.HIGH_PRIORITY
                else:
                    reason = ScheduleDecisionReason.PERIODIC_REFRESH
                
                # Update or create priority record
                priority = db.query(CompanyPriority).filter(
                    CompanyPriority.cik == company.cik
                ).first()
                
                if not priority:
                    priority = CompanyPriority(
                        cik=company.cik,
                        company_name=company.name
                    )
                    db.add(priority)
                
                priority.market_cap = company.market_cap
                priority.industry = company.industry
                priority.sector = company.sector
                priority.times_analyzed = times_analyzed
                priority.last_analyzed_at = last_analyzed_at
                priority.next_scheduled_at = next_scheduled
                priority.priority_score = priority_score
                priority.priority_reason = reason
                priority.avg_product_match_score = avg_score
                priority.total_pain_points_found = total_pains
                priority.has_high_value_matches = has_high_value
                priority.last_priority_update = datetime.utcnow()
            
            db.commit()
            logger.info(f"✅ Updated priorities for {len(companies)} companies")
