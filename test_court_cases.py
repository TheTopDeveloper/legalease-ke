"""
Test script for retrieving court cases from the Kenya Law website.
This script focuses specifically on testing the case law retrieval functionality.
"""

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

def test_supreme_court_cases():
    """Test retrieving cases from the Supreme Court"""
    logger.info("Testing Supreme Court case retrieval...")
    
    # Initialize scraper
    scraper = KenyaLawScraper()
    
    # Get Supreme Court cases
    court_code = "KESC"
    limit = 3
    logger.info(f"Fetching {limit} cases from {court_code}...")
    
    supreme_court_cases = scraper.get_case_law(court_code, limit=limit)
    
    if supreme_court_cases:
        logger.info(f"Success! Retrieved {len(supreme_court_cases)} Supreme Court cases")
        
        # Display case details
        for i, case in enumerate(supreme_court_cases):
            logger.info(f"\nCase {i+1}:")
            logger.info(f"  Title: {case.get('title', 'No title')}")
            logger.info(f"  Link: {case.get('link', 'No link')}")
            logger.info(f"  Court: {case.get('court', 'No court')}")
            logger.info(f"  Date: {case.get('date', 'No date')}")
            
        return supreme_court_cases
    else:
        logger.error("Failed to retrieve Supreme Court cases")
        return None

def test_legislation():
    """Test retrieving legislation"""
    logger.info("\nTesting legislation retrieval...")
    
    # Initialize scraper
    scraper = KenyaLawScraper()
    
    # Get legislation
    limit = 3
    logger.info(f"Fetching {limit} legislation items...")
    
    legislation = scraper.get_legislation(limit=limit)
    
    if legislation:
        logger.info(f"Success! Retrieved {len(legislation)} legislation items")
        
        # Display legislation details
        for i, law in enumerate(legislation):
            logger.info(f"\nLegislation {i+1}:")
            logger.info(f"  Title: {law.get('title', 'No title')}")
            logger.info(f"  Link: {law.get('link', 'No link')}")
            
        return legislation
    else:
        logger.error("Failed to retrieve legislation")
        return None

def run_tests():
    """Run the test script"""
    logger.info("=== STARTING KENYA LAW COURT CASES TEST ===\n")
    
    supreme_court_cases = test_supreme_court_cases()
    legislation_items = test_legislation()
    
    logger.info("\n=== TEST SUMMARY ===")
    logger.info(f"Supreme Court cases: {len(supreme_court_cases) if supreme_court_cases else 0} retrieved")
    logger.info(f"Legislation items: {len(legislation_items) if legislation_items else 0} retrieved")
    
    logger.info("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    run_tests()