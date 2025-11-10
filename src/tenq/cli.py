"""
CLI tool to run 10-Q analysis pipeline.

Usage:
    python -m src.tenq.cli "Apple Inc"
"""
import asyncio
import json
import sys
from .dag import analyze_10q
from ..utils.logging import setup_logger

logger = setup_logger(__name__)


async def main():
    """Run 10-Q analysis from command line."""
    if len(sys.argv) < 2:
        print("Usage: python -m src.tenq.cli 'Company Name'")
        print("\nExample: python -m src.tenq.cli 'Apple Inc'")
        return 1
    
    company_name = sys.argv[1]
    
    print(f"\n{'='*60}")
    print(f"10-Q Analysis Pipeline")
    print(f"{'='*60}\n")
    print(f"Company: {company_name}\n")
    
    try:
        # Run analysis
        result = await analyze_10q(company_name)
        
        if result.get("error"):
            print(f"\n❌ Error: {result['error']}\n")
            return 1
        
        # Display results
        print(f"\n{'='*60}")
        print("📊 Results")
        print(f"{'='*60}\n")
        
        if result.get("filing_metadata"):
            metadata = result["filing_metadata"]
            print(f"Filing Date: {metadata.get('file_date')}")
            print(f"Reporting Date: {metadata.get('reporting_date')}")
            print(f"CIK: {metadata.get('cik')}\n")
        
        if result.get("pain_points"):
            print(f"\n🔍 Pain Points ({len(result['pain_points'])} found):")
            print("-" * 60)
            for i, pp in enumerate(result["pain_points"], 1):
                print(f"\n{i}. [{pp.get('severity', 'N/A').upper()}] {pp.get('category', 'N/A')}")
                print(f"   {pp.get('description', 'N/A')[:150]}...")
        
        if result.get("matched_solutions"):
            print(f"\n\n🎯 Matched Solutions ({len(result['matched_solutions'])} found):")
            print("-" * 60)
            for i, match in enumerate(result["matched_solutions"][:5], 1):
                solution = match.get("solution", {})
                print(f"\n{i}. {solution.get('name')} (Relevance: {match.get('relevance_score', 0):.2f})")
                print(f"   {solution.get('value_proposition', 'N/A')[:150]}...")
        
        if result.get("insights"):
            print(f"\n\n💡 Sales Insights ({len(result['insights'])} generated):")
            print("-" * 60)
            for i, insight in enumerate(result["insights"], 1):
                print(f"\n{i}. {insight.get('recommended_solution')} [{insight.get('priority', 'N/A').upper()}]")
                print(f"   Pain Point: {insight.get('pain_point_summary', 'N/A')[:100]}...")
                print(f"   Strategy: {insight.get('engagement_strategy', 'N/A')[:200]}...")
        
        # Save to JSON file
        output_file = f"10q_analysis_{company_name.replace(' ', '_').replace(',', '')}.json"
        with open(output_file, "w") as f:
            json.dump({
                "company_name": result["company_name"],
                "filing_metadata": result.get("filing_metadata"),
                "pain_points": result.get("pain_points"),
                "matched_solutions": result.get("matched_solutions"),
                "insights": result.get("insights")
            }, f, indent=2, default=str)
        
        print(f"\n\n✅ Results saved to: {output_file}")
        print(f"\n{'='*60}\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error running analysis: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
