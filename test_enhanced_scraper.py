"""
Test script for the enhanced Kenya Law scraper.
This script tests the scraper's ability to retrieve cases, legislation, and perform searches.
"""

import json
import logging
import sys
from utils.scraper import KenyaLawScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def test_search():
    """Test the Kenya Law search functionality"""
    logger.info("Testing Kenya Law search...")
    
    # Initialize scraper
    scraper = KenyaLawScraper()
    
    # Test search
    query = "corruption"
    logger.info(f"Searching for '{query}'...")
    results = scraper.search_cases(query)
    
    if results:
        logger.info(f"Search successful! Found {len(results)} results for '{query}'")
        for i, result in enumerate(results[:3]):  # Show first 3 results
            logger.info(f"Result {i+1}: {result.get('title', 'No title')}")
    else:
        logger.error(f"Search failed. No results found for '{query}'")
    
    return results

def test_court_cases():
    """Test retrieving cases from specific courts"""
    # Initialize scraper
    scraper = KenyaLawScraper()
    
    # Test different court codes
    court_codes = ["KESC", "KECA", "KEHC"]
    all_results = {}
    
    for court_code in court_codes:
        logger.info(f"Testing case retrieval for {court_code}...")
        
        court_cases = scraper.get_case_law(court_code, limit=5)
        all_results[court_code] = court_cases
        
        if court_cases:
            logger.info(f"Court case retrieval successful! Found {len(court_cases)} cases from {court_code}")
            for i, case in enumerate(court_cases[:3]):  # Show first 3 cases
                logger.info(f"Case {i+1}: {case.get('title', 'No title')}")
        else:
            logger.error(f"Court case retrieval failed. No cases found for {court_code}")
    
    return all_results

def test_legislation():
    """Test retrieving legislation"""
    logger.info("Testing legislation retrieval...")
    
    # Initialize scraper
    scraper = KenyaLawScraper()
    
    legislation = scraper.get_legislation(limit=10)
    
    if legislation:
        logger.info(f"Legislation retrieval successful! Found {len(legislation)} legislation items")
        for i, law in enumerate(legislation[:5]):  # Show first 5 legislation items
            logger.info(f"Legislation {i+1}: {law.get('title', 'No title')}")
    else:
        logger.error("Legislation retrieval failed. No legislation found")
    
    return legislation

def test_detailed_case():
    """Test retrieving detailed case information"""
    logger.info("Testing detailed case retrieval...")
    
    # Initialize scraper
    scraper = KenyaLawScraper()
    
    # First get a list of cases
    court_cases = scraper.get_case_law("KESC", limit=1)
    
    if not court_cases:
        logger.error("Could not retrieve any cases to test detailed view")
        return None
    
    # Get the URL of the first case
    case_url = court_cases[0].get('link')
    
    if not case_url:
        logger.error("Case URL not found in retrieved case")
        return None
    
    logger.info(f"Retrieving detailed information for case: {court_cases[0].get('title', 'Unknown case')}")
    
    case_details = scraper.get_case_details(case_url)
    
    if case_details:
        logger.info("Case detail retrieval successful!")
        logger.info(f"Case title: {case_details.get('title', 'No title')}")
        logger.info(f"Case citation: {case_details.get('citation', 'No citation')}")
        logger.info(f"Content length: {len(case_details.get('content', ''))}")
    else:
        logger.error(f"Case detail retrieval failed for URL: {case_url}")
    
    return case_details

def run_all_tests():
    """Run all tests"""
    logger.info("\n=== STARTING ENHANCED KENYA LAW SCRAPER TESTS ===\n")
    
    logger.info("\n--- Testing Search ---\n")
    search_results = test_search()
    
    logger.info("\n--- Testing Court Cases ---\n")
    court_results = test_court_cases()
    
    logger.info("\n--- Testing Legislation ---\n")
    legislation_results = test_legislation()
    
    logger.info("\n--- Testing Detailed Case ---\n")
    detailed_case = test_detailed_case()
    
    logger.info("\n=== ALL TESTS COMPLETED ===\n")
    
    # Summary
    logger.info("Summary of findings:")
    logger.info(f"- Search query: {len(search_results) if search_results else 0} results")
    
    for court, cases in court_results.items():
        logger.info(f"- {court}: {len(cases) if cases else 0} cases")
    
    logger.info(f"- Legislation: {len(legislation_results) if legislation_results else 0} items")
    logger.info(f"- Detailed case: {'Retrieved successfully' if detailed_case else 'Failed to retrieve'}")
    
    return {
        'search_results': search_results,
        'court_results': court_results,
        'legislation_results': legislation_results,
        'detailed_case': detailed_case
    }

if __name__ == "__main__":
    run_all_tests()