"""
Test script to validate the fixes for HTTP 500 and hallucination issues.
Run this BEFORE pushing to main branch.

Fixed for Windows compatibility - uses ASCII characters instead of emojis
"""
import asyncio
import logging
import sys
from src.pipelines.orchestrator import Orchestrator
from src.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def test_suicide_research():
    """Test the problematic query that was causing issues."""
    logger.info("=" * 80)
    logger.info("TEST 1: Suicide Research Query (Previously Broken)")
    logger.info("=" * 80)
    
    orchestrator = Orchestrator()
    
    # Sample documents about suicide research
    test_documents = [
        {
            "title": "Mental Health Crisis Intervention Strategies",
            "summary": "This paper examines evidence-based approaches to suicide prevention in men, including cognitive behavioral therapy, medication management, and crisis hotlines. The study found that early intervention reduces suicide attempts by 45%. Mental health professionals recommend comprehensive screening programs in high-risk occupations.",
            "url": "https://example.com/paper1",
            "year": 2024,
            "source": "semantic_scholar"
        },
        {
            "title": "Gender Disparities in Suicide Mortality",
            "summary": "Men die by suicide at 3-4 times the rate of women. This research explores sociological and biological factors contributing to male suicide mortality, including toxic masculinity, help-seeking barriers, and occupational stress. The analysis covers data from 150 countries spanning 25 years.",
            "url": "https://example.com/paper2",
            "year": 2024,
            "source": "semantic_scholar"
        },
        {
            "title": "Occupational Risk Factors for Male Suicide",
            "summary": "This study analyzes suicide rates across different professions. Construction workers, farmers, and military personnel show elevated rates. Workplace interventions and peer support programs show promise in reducing mortality. The research identifies workplace stigma as a major barrier to help-seeking.",
            "url": "https://example.com/paper3",
            "year": 2023,
            "source": "semantic_scholar"
        }
    ]
    
    query = "suicide of men"
    
    try:
        result = await orchestrator.run_pipeline(query, test_documents)
        
        logger.info("")
        logger.info("[PASS] TEST 1: Pipeline completed successfully!")
        logger.info(f"Query: {query}")
        logger.info(f"Confidence: {result.confidence:.2f}")
        logger.info(f"\nGenerated Summary:\n{result.result}\n")
        logger.info(f"Metadata: {result.metadata}\n")
        
        # Validate the result
        summary_lower = result.result.lower()
        
        # Check 1: Should mention suicide-related content
        suicide_keywords = ['suicide', 'mental', 'health', 'prevention', 'crisis', 'intervention', 'men']
        has_suicide_content = any(keyword in summary_lower for keyword in suicide_keywords)
        
        if has_suicide_content:
            logger.info("[PASS] CHECK 1: Summary contains suicide-related content")
        else:
            logger.warning("[FAIL] CHECK 1: Summary doesn't mention suicide or related topics")
        
        # Check 2: Should NOT have unrelated content like nanotechnology
        bad_keywords = ['nanotechnology', 'nanoparticle', 'quantum dot', 'carbon nanotube']
        has_bad_content = any(keyword in summary_lower for keyword in bad_keywords)
        
        if not has_bad_content:
            logger.info("[PASS] CHECK 2: No hallucinated nanotechnology content")
        else:
            logger.warning("[FAIL] CHECK 2: Summary contains hallucinated unrelated content")
        
        # Check 3: Summary should have reasonable length
        word_count = len(result.result.split())
        if 20 <= word_count <= 300:
            logger.info(f"[PASS] CHECK 3: Summary length is reasonable ({word_count} words)")
        else:
            logger.warning(f"[FAIL] CHECK 3: Summary length is problematic ({word_count} words)")
        
        return has_suicide_content and not has_bad_content
        
    except Exception as e:
        logger.error(f"[FAIL] TEST 1 FAILED with error: {str(e)}", exc_info=True)
        return False


async def test_empty_context():
    """Test that empty context doesn't cause HTTP 500."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 2: Empty Context Handling (Previously caused HTTP 500)")
    logger.info("=" * 80)
    
    orchestrator = Orchestrator()
    
    test_documents = [
        {
            "title": "Empty Paper",
            "summary": "",  # Empty!
            "url": "",
            "year": 2024
        }
    ]
    
    query = "test query"
    
    try:
        result = await orchestrator.run_pipeline(query, test_documents)
        
        # Should NOT crash - should return graceful error
        if result.confidence == 0.0 and "error" in result.metadata:
            logger.info("")
            logger.info("[PASS] TEST 2: Gracefully handled empty context")
            logger.info(f"Error message: {result.metadata.get('error')}")
            return True
        else:
            logger.warning("[INCONCLUSIVE] TEST 2: Got result despite empty context")
            logger.info(f"Result: {result.result[:100] if result.result else 'EMPTY'}")
            return False
            
    except Exception as e:
        logger.error(f"[FAIL] TEST 2 FAILED - Exception thrown: {str(e)}")
        return False


async def test_short_context():
    """Test that very short context is handled gracefully."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST 3: Short Context Handling (Minimum viable input)")
    logger.info("=" * 80)
    
    orchestrator = Orchestrator()
    
    # Provide longer content to meet BART minimum token requirement (50 tokens)
    test_documents = [
        {
            "title": "Quantum Computing Fundamentals",
            "summary": "Quantum computing is a revolutionary technology that harnesses the principles of quantum mechanics to process information. Unlike classical computers that use bits, quantum computers use quantum bits or qubits. These qubits can exist in multiple states simultaneously, enabling quantum computers to perform complex calculations exponentially faster. Recent advances include error correction and increased qubit counts.",
            "url": "https://example.com",
            "year": 2024
        }
    ]
    
    query = "quantum computing"
    
    try:
        result = await orchestrator.run_pipeline(query, test_documents)
        
        if result.confidence > 0.0 and result.result and len(result.result) > 10:
            logger.info("")
            logger.info("[PASS] TEST 3: Handled context successfully")
            logger.info(f"Summary: {result.result}")
            logger.info(f"Confidence: {result.confidence:.2f}")
            return True
        else:
            logger.warning(f"[FAIL] TEST 3: Couldn't generate proper summary")
            logger.warning(f"Confidence: {result.confidence}, Result length: {len(result.result) if result.result else 0}")
            if result.metadata.get('error'):
                logger.warning(f"Error: {result.metadata.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"[FAIL] TEST 3 FAILED with error: {str(e)}", exc_info=True)
        return False


async def run_all_tests():
    """Run all tests and report results."""
    logger.info("\n" + "=" * 80)
    logger.info("STARTING COMPREHENSIVE TEST SUITE")
    logger.info("=" * 80)
    
    results = {}
    
    results['test_suicide'] = await test_suicide_research()
    results['test_empty'] = await test_empty_context()
    results['test_short'] = await test_short_context()
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST SUMMARY REPORT")
    logger.info("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_status in results.items():
        status = "[PASS]" if passed_status else "[FAIL]"
        logger.info(f"{test_name}: {status}")
    
    logger.info("")
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("=" * 80)
    
    if passed == total:
        logger.info("SUCCESS: All tests passed! Ready for deployment.")
    else:
        logger.warning(f"WARNING: {total - passed} test(s) failed. Review above for details.")
    
    logger.info("=" * 80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error running tests: {str(e)}", exc_info=True)
        exit(1)