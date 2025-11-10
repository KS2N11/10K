"""
Nodes for the 10-Q analysis pipeline.
"""
import os
import json
import requests
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from bs4 import BeautifulSoup

from ..utils.logging import setup_logger
from ..utils.llm_factory import get_factory
from .schemas import TenQState, PainPoint, Solution, MatchedSolution, Insight

logger = setup_logger(__name__)

# Get factory instance
factory = get_factory()


# ============================================================================
# Node 1: Fetch 10-Q Filing
# ============================================================================

def fetch_10q_node(state: TenQState) -> TenQState:
    """Fetch 10-Q filing from SEC."""
    logger.info(f"📥 Fetching 10-Q for {state['company_name']}")
    
    try:
        # Import the fetcher from the tenq module
        from .fetcher import get_latest_10q
        
        # Fetch the filing
        filing_metadata = get_latest_10q(state["company_name"])
        
        if not filing_metadata:
            state["error"] = f"Could not find 10-Q filing for {state['company_name']}"
            return state
        
        state["filing_metadata"] = filing_metadata
        state["cik"] = filing_metadata["cik"]
        
        # The viewer URL gives us an interactive page, we need the actual document
        # Build the Archives URL to get the filing documents index
        acc_no_raw = filing_metadata["acc_no"]  # Without dashes
        acc_no_with_dashes = filing_metadata.get("acc_no_raw", f"{acc_no_raw[:10]}-{acc_no_raw[10:12]}-{acc_no_raw[12:]}")  # With dashes
        cik_num = str(int(filing_metadata["cik"]))
        
        # Build URLs
        base_archives_url = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_no_raw}/"
        index_url = base_archives_url + f"{acc_no_with_dashes}-index.htm"
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": os.getenv("SEC_USER_AGENT", "10Q Insight Agent")
        })
        
        primary_doc_url = None
        
        # Fetch the filing index page
        try:
            index_response = session.get(index_url)
            if index_response.status_code == 200:
                # Parse the index to find the primary document
                soup = BeautifulSoup(index_response.text, 'html.parser')
                
                # Look for the document table
                table = soup.find('table', {'class': 'tableFile'})
                if table:
                    rows = table.find_all('tr')[1:]  # Skip header row
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            seq = cells[0].text.strip()
                            form_type = cells[1].text.strip()
                            doc_name_cell = cells[2].text.strip()
                            description = cells[3].text.strip()
                            
                            # Extract just the filename (before any extra text like "iXBRL")
                            doc_name = doc_name_cell.split()[0] if doc_name_cell else ""
                            
                            # Get the first .htm file (sequence 1, form type 10-Q)
                            if seq == "1" and doc_name.endswith('.htm') and form_type == "10-Q":
                                primary_doc_url = base_archives_url + doc_name
                                logger.info(f"📄 Found primary document: {doc_name}")
                                break
        except Exception as e:
            logger.warning(f"⚠️ Error fetching index: {e}")
        
        if not primary_doc_url:
            state["error"] = "Could not find primary 10-Q document"
            logger.error(f"❌ Could not locate primary document for {filing_metadata['acc_no']}")
            return state
        
        # Fetch the actual document content
        response = session.get(primary_doc_url)
        response.raise_for_status()
        
        state["filing_content"] = response.text
        logger.info(f"✅ Fetched 10-Q from {primary_doc_url} ({len(state['filing_content'])} characters)")
        
    except Exception as e:
        logger.error(f"❌ Error fetching 10-Q: {e}")
        state["error"] = str(e)
    
    return state


# ============================================================================
# Node 2: Parse 10-Q Sections
# ============================================================================

def parse_10q_node(state: TenQState) -> TenQState:
    """Parse and extract key sections from 10-Q filing."""
    logger.info("📄 Parsing 10-Q sections")
    
    if not state.get("filing_content"):
        state["error"] = "No filing content to parse"
        return state
    
    try:
        content = state["filing_content"]
        
        # Simple section extraction based on common 10-Q structure
        # In a production system, you'd use a more sophisticated parser
        sections = {
            "full_text": content[:50000],  # Limit to first 50k chars for now
            "metadata": {
                "company": state["company_name"],
                "cik": state["cik"],
                "filing_date": state["filing_metadata"]["file_date"],
                "reporting_date": state["filing_metadata"]["reporting_date"]
            }
        }
        
        state["parsed_sections"] = sections
        logger.info("✅ Parsed 10-Q sections")
        
    except Exception as e:
        logger.error(f"❌ Error parsing 10-Q: {e}")
        state["error"] = str(e)
    
    return state


# ============================================================================
# Node 3: Embed Content
# ============================================================================

async def embed_content_node(state: TenQState) -> TenQState:
    """Chunk and embed 10-Q content."""
    logger.info("🔢 Embedding 10-Q content")
    
    if not state.get("parsed_sections"):
        state["error"] = "No parsed sections to embed"
        return state
    
    try:
        # Get content
        content = state["parsed_sections"]["full_text"]
        
        # Chunk the content
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        chunks = text_splitter.split_text(content)
        
        # Get embeddings manager
        embedder = factory.create_embedder()
        
        # Embed chunks (async)
        embeddings = await embedder.embed_documents(chunks)
        
        state["embeddings"] = [
            {"text": chunk, "embedding": emb}
            for chunk, emb in zip(chunks, embeddings)
        ]
        
        logger.info(f"✅ Created {len(embeddings)} embeddings")
        
    except Exception as e:
        logger.error(f"❌ Error embedding content: {e}")
        state["error"] = str(e)
    
    return state


# ============================================================================
# Node 4: Extract Pain Points
# ============================================================================

async def extract_pain_points_node(state: TenQState) -> TenQState:
    """Extract business pain points from 10-Q using LLM."""
    logger.info("🔍 Extracting pain points")
    
    if not state.get("parsed_sections"):
        state["error"] = "No parsed sections available"
        return state
    
    try:
        llm = factory.create_llm_manager()
        
        content = state["parsed_sections"]["full_text"]
        quarter = state["filing_metadata"]["reporting_date"]
        
        system_message = SystemMessage(content="""You are an expert business analyst specializing in analyzing quarterly financial reports (10-Q filings).
Your task is to identify key business pain points, challenges, and areas of concern from the 10-Q filing.

Focus on:
- Revenue declines or growth challenges
- Operational inefficiencies
- Market risks and competitive pressures
- Cost management issues
- Supply chain disruptions
- Technology or infrastructure challenges
- Regulatory or compliance concerns
- Customer retention or acquisition issues

For each pain point, provide:
1. Category (e.g., revenue_decline, operational_challenges, market_risks)
2. Clear description
3. Severity level (low, medium, high, critical)
4. Evidence from the filing

Return a JSON array of pain points.""")
        
        user_message = HumanMessage(content=f"""Analyze this 10-Q filing excerpt and extract key business pain points:

Company: {state['company_name']}
Quarter: {quarter}

Filing Content (first 3000 characters):
{content[:3000]}

Return a JSON array with this structure:
[
  {{
    "category": "category_name",
    "description": "detailed description",
    "severity": "low|medium|high|critical",
    "evidence": "quote from filing",
    "quarter": "{quarter}"
  }}
]""")
        
        response = await llm.ainvoke([system_message, user_message])
        
        # Parse JSON response
        try:
            # Try to extract JSON from response
            json_start = response.find("[")
            json_end = response.rfind("]") + 1
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                pain_points_data = json.loads(json_str)
            else:
                # Fallback: create structured response
                pain_points_data = [{
                    "category": "general_challenges",
                    "description": response[:500],
                    "severity": "medium",
                    "evidence": "See full analysis",
                    "quarter": quarter
                }]
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from LLM response, using fallback")
            pain_points_data = [{
                "category": "general_challenges",
                "description": response[:500],
                "severity": "medium",
                "evidence": "See full analysis",
                "quarter": quarter
            }]
        
        state["pain_points"] = pain_points_data
        logger.info(f"✅ Extracted {len(pain_points_data)} pain points")
        
    except Exception as e:
        logger.error(f"❌ Error extracting pain points: {e}")
        state["error"] = str(e)
    
    return state


# ============================================================================
# Node 5: Match Solutions
# ============================================================================

def match_solutions_node(state: TenQState) -> TenQState:
    """Match pain points with solutions from catalog."""
    logger.info("🎯 Matching solutions to pain points")
    
    if not state.get("pain_points"):
        state["error"] = "No pain points to match"
        return state
    
    try:
        # Load solutions catalog
        catalog_path = os.path.join(os.path.dirname(__file__), "solutions_catalog.json")
        with open(catalog_path, "r") as f:
            catalog = json.load(f)
        
        solutions = catalog["solutions"]
        pain_points = state["pain_points"]
        
        matched = []
        
        for pain_point in pain_points:
            # Simple keyword-based matching
            # In production, use embeddings for better matching
            pain_category = pain_point.get("category", "").lower()
            
            for solution in solutions:
                addressed_points = [p.lower() for p in solution["pain_points_addressed"]]
                
                # Check if pain point category matches any addressed points
                relevance = 0.0
                for addressed in addressed_points:
                    if pain_category in addressed or addressed in pain_category:
                        relevance = 0.8
                        break
                    # Partial match
                    elif any(word in addressed for word in pain_category.split("_")):
                        relevance = max(relevance, 0.5)
                
                if relevance > 0.4:
                    matched.append({
                        "pain_point": pain_point,
                        "solution": solution,
                        "relevance_score": relevance,
                        "matching_rationale": f"{solution['name']} addresses {pain_category} challenges"
                    })
        
        # Sort by relevance
        matched.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        state["matched_solutions"] = matched
        logger.info(f"✅ Matched {len(matched)} solutions")
        
    except Exception as e:
        logger.error(f"❌ Error matching solutions: {e}")
        state["error"] = str(e)
    
    return state


# ============================================================================
# Node 6: Generate Insights
# ============================================================================

async def generate_insights_node(state: TenQState) -> TenQState:
    """Generate actionable sales insights."""
    logger.info("💡 Generating sales insights")
    
    if not state.get("matched_solutions"):
        state["error"] = "No matched solutions available"
        return state
    
    try:
        llm = factory.create_llm_manager()
        
        matched_solutions = state["matched_solutions"][:5]  # Top 5
        quarter = state["filing_metadata"]["reporting_date"]
        
        insights = []
        
        for match in matched_solutions:
            pain_point = match["pain_point"]
            solution = match["solution"]
            
            system_message = SystemMessage(content="""You are a B2B sales strategist creating actionable sales insights.
Generate a concise, compelling sales insight that:
1. Summarizes the pain point
2. Explains how the solution addresses it
3. Provides a specific engagement strategy
4. Assigns a priority level

Be specific, actionable, and focus on business value.""")
            
            user_message = HumanMessage(content=f"""Create a sales insight:

Company: {state['company_name']}
Quarter: {quarter}

Pain Point: {pain_point['description']}
Severity: {pain_point['severity']}

Solution: {solution['name']}
Value Proposition: {solution['value_proposition']}

Provide:
1. Brief pain point summary (1 sentence)
2. Recommended solution (1 sentence)
3. Value proposition (1 sentence)
4. Engagement strategy (2-3 sentences on how to approach the client)
5. Priority (low, medium, high, urgent)""")
            
            response = await llm.ainvoke([system_message, user_message])
            
            insights.append({
                "company_name": state["company_name"],
                "quarter": quarter,
                "pain_point_summary": pain_point["description"][:200],
                "recommended_solution": solution["name"],
                "value_proposition": solution["value_proposition"],
                "engagement_strategy": response,
                "priority": pain_point["severity"],
                "relevance_score": match["relevance_score"]
            })
        
        state["insights"] = insights
        logger.info(f"✅ Generated {len(insights)} insights")
        
    except Exception as e:
        logger.error(f"❌ Error generating insights: {e}")
        state["error"] = str(e)
    
    return state
