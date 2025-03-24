"""
Test script for the Kenya Law web scraper.
This script tests the functionality of the scraper to retrieve legal content.
"""
import sys
import json
from utils.scraper import KenyaLawScraper
from config import COURT_LEVELS

def test_scraper():
    """Test the Kenya Law scraper functionality"""
    print("=== Kenya Law Scraper Test ===\n")
    
    scraper = KenyaLawScraper()
    
    # Test getting case law from Supreme Court
    print("Testing case law retrieval from Supreme Court...")
    court_code = COURT_LEVELS["Supreme Court"]
    cases = scraper.get_case_law(court_code, limit=3)
    
    if cases:
        print(f"✓ Successfully retrieved {len(cases)} cases from Supreme Court")
        print("\nSample case:")
        print(f"  Title: {cases[0]['title']}")
        print(f"  Link: {cases[0]['link']}")
        print("  Metadata:")
        for key, value in cases[0].get('metadata', {}).items():
            print(f"    {key}: {value}")
    else:
        print("✗ Failed to retrieve cases from Supreme Court")
    
    # Test searching for a legal term
    print("\nTesting case search functionality...")
    search_term = "constitutional rights"
    search_results = scraper.search_cases(search_term, page=1)
    
    if search_results:
        print(f"✓ Successfully found {len(search_results)} results for search term '{search_term}'")
        print("\nSample search result:")
        print(f"  Title: {search_results[0]['title']}")
        print(f"  Link: {search_results[0]['link']}")
        print(f"  Excerpt: {search_results[0]['excerpt'][:100]}...")
    else:
        print(f"✗ No search results found for '{search_term}'")
    
    # Test getting legislation
    print("\nTesting legislation retrieval...")
    legislation = scraper.get_legislation(limit=3)
    
    if legislation:
        print(f"✓ Successfully retrieved {len(legislation)} legislation items")
        print("\nSample legislation:")
        print(f"  Title: {legislation[0]['title']}")
        print(f"  Link: {legislation[0]['link']}")
    else:
        print("✗ Failed to retrieve legislation")
    
    # Test extracting text content from a URL
    print("\nTesting text extraction from a webpage...")
    if search_results:
        sample_url = search_results[0]['link']
        print(f"Extracting text from: {sample_url}")
        text_content = scraper.get_website_text_content(sample_url)
        
        if text_content:
            print(f"✓ Successfully extracted {len(text_content)} characters of text content")
            print("\nSample text (first 200 characters):")
            print(f"  {text_content[:200]}...")
        else:
            print("✗ Failed to extract text content")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_scraper()