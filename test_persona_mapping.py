"""
Simple unit test to verify persona mapping logic works correctly.
Tests the determine_persona function without running full workflow.
"""
from src.nodes.solution_matcher.pitch_writer import determine_persona
from src.nodes.solution_matcher.fit_scorer import categorize_product

def test_categorize_product():
    """Test product categorization logic."""
    print("="*80)
    print("TESTING PRODUCT CATEGORIZATION")
    print("="*80)
    
    test_cases = [
        {
            "name": "Enterprise Cybersecurity Suite",
            "capabilities": ["threat detection", "encryption", "compliance"],
            "expected": "Security & Compliance"
        },
        {
            "name": "Cloud Migration & Optimization",
            "capabilities": ["cloud migration", "infrastructure", "devops"],
            "expected": "Infrastructure & Cloud"
        },
        {
            "name": "AI Innovation Suite",
            "capabilities": ["predictive analytics", "nlp", "computer vision"],
            "expected": "AI & Machine Learning"
        },
        {
            "name": "Data & Analytics Platform",
            "capabilities": ["data warehouse", "etl", "dashboards"],
            "expected": "Data & Analytics"
        },
        {
            "name": "Financial Management System",
            "capabilities": ["budgeting", "forecasting", "reporting"],
            "expected": "Finance & Accounting"
        },
        {
            "name": "Digital Transformation Services",
            "capabilities": ["process digitization", "workflow automation"],
            "expected": "Consulting & Strategy"
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        category = categorize_product(test["name"], test["capabilities"])
        status = "✓" if category == test["expected"] else "✗"
        
        if category == test["expected"]:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} {test['name']}")
        print(f"  Expected: {test['expected']}")
        print(f"  Got: {category}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed} passed, {failed} failed")
    print("="*80)
    
    return failed == 0

def test_persona_assignment():
    """Test persona assignment logic."""
    print("\n\n" + "="*80)
    print("TESTING PERSONA ASSIGNMENT")
    print("="*80)
    
    test_cases = [
        {
            "product": "Enterprise Cybersecurity Suite",
            "category": "Security & Compliance",
            "expected": "CISO"
        },
        {
            "product": "Cloud Migration",
            "category": "Infrastructure & Cloud",
            "expected": "CTO"
        },
        {
            "product": "AI Innovation Suite",
            "category": "AI & Machine Learning",
            "expected": "CTO"
        },
        {
            "product": "Data Analytics Platform",
            "category": "Data & Analytics",
            "expected": "CTO"
        },
        {
            "product": "Financial Management System",
            "category": "Finance & Accounting",
            "expected": "CFO"
        },
        {
            "product": "Supply Chain Optimization",
            "category": "Supply Chain & Logistics",
            "expected": "VP of Operations"  # Keyword "supply" should trigger this
        },
        {
            "product": "Customer Experience Platform",
            "category": "Customer Experience",
            "expected": "VP of Customer Success"  # This is more specific and appropriate
        },
        {
            "product": "Talent Management",
            "category": "Human Resources",
            "expected": "CHRO"
        },
        {
            "product": "Digital Transformation",
            "category": "Consulting & Strategy",
            "expected": "CEO"
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        matches = [{
            "product_name": test["product"],
            "product_category": test["category"]
        }]
        
        persona = determine_persona(matches, [])
        status = "✓" if persona == test["expected"] else "✗"
        
        if persona == test["expected"]:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} {test['product']} ({test['category']})")
        print(f"  Expected: {test['expected']}")
        print(f"  Got: {persona}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed} passed, {failed} failed")
    print("="*80)
    
    return failed == 0

def test_keyword_based_persona():
    """Test keyword-based persona assignment (overrides category)."""
    print("\n\n" + "="*80)
    print("TESTING KEYWORD-BASED PERSONA OVERRIDE")
    print("="*80)
    
    test_cases = [
        {
            "product": "Advanced Cybersecurity Protection",
            "category": "Other",
            "expected": "CISO",
            "reason": "'cybersecurity' keyword should trigger CISO"
        },
        {
            "product": "AI-Powered Analytics",
            "category": "Other",
            "expected": "CTO",
            "reason": "'ai' keyword should trigger CTO"
        },
        {
            "product": "Financial Planning Software",
            "category": "Other",
            "expected": "CFO",
            "reason": "'financial' keyword should trigger CFO"
        },
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        matches = [{
            "product_name": test["product"],
            "product_category": test["category"]
        }]
        
        persona = determine_persona(matches, [])
        status = "✓" if persona == test["expected"] else "✗"
        
        if persona == test["expected"]:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{status} {test['product']}")
        print(f"  Reason: {test['reason']}")
        print(f"  Expected: {test['expected']}")
        print(f"  Got: {persona}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed} passed, {failed} failed")
    print("="*80)
    
    return failed == 0

if __name__ == "__main__":
    print("\n" + "#"*80)
    print("# PERSONA MAPPING & CATEGORIZATION TEST SUITE")
    print("#"*80)
    print("\nThis test verifies:")
    print("  1. Product categorization based on name and capabilities")
    print("  2. Persona assignment based on product category")
    print("  3. Keyword-based persona override (e.g., 'cybersecurity' → CISO)")
    print("\n" + "#"*80 + "\n")
    
    # Run all tests
    test1 = test_categorize_product()
    test2 = test_persona_assignment()
    test3 = test_keyword_based_persona()
    
    # Final summary
    print("\n\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80)
    print(f"Product Categorization: {'✓ PASS' if test1 else '✗ FAIL'}")
    print(f"Persona Assignment: {'✓ PASS' if test2 else '✗ FAIL'}")
    print(f"Keyword Override: {'✓ PASS' if test3 else '✗ FAIL'}")
    print("="*80)
    
    if test1 and test2 and test3:
        print("\n🎉 ALL TESTS PASSED! Persona mapping is working correctly.")
        print("\nKey improvements:")
        print("  ✓ Cybersecurity products → CISO (not CFO)")
        print("  ✓ Cloud/AI/Data products → CTO")
        print("  ✓ Financial products → CFO")
        print("  ✓ Supply chain products → VP of Operations")
        print("  ✓ HR products → CHRO")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED. Review the results above.")
        exit(1)
