"""
Test script for the enhanced legal research functionality.
This script tests the search, research, and analysis features.
"""

import json
import logging
import sys
from models import User, db, LegalResearch
from utils.research_assistant import LegalResearchAssistant
from utils.scraper import KenyaLawScraper
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def create_test_user():
    """Create a test user with tokens for testing"""
    with app.app_context():
        # Check if test user exists
        user = User.query.filter_by(username="test_research").first()
        if not user:
            user = User(
                username="test_research",
                email="test_research@example.com",
                first_name="Test",
                last_name="Research",
                role="individual",
                account_type="premium",
                tokens_available=100
            )
            user.set_password("test123")
            db.session.add(user)
            db.session.commit()
            logger.info("Created test user for research testing")
        else:
            # Ensure user has enough tokens
            if user.tokens_available < 100:
                user.tokens_available = 100
                db.session.commit()
                logger.info("Updated test user tokens to 100")
        
        return user.id

def test_search():
    """Test the Kenya Law search functionality"""
    logger.info("Testing Kenya Law search...")
    
    # Initialize scraper
    scraper = KenyaLawScraper()
    
    # Test search
    query = "corruption"
    results = scraper.search_cases(query)
    
    if results:
        logger.info(f"Search successful! Found {len(results)} results for '{query}'")
        logger.info(f"First result: {results[0].get('title', 'No title')}")
    else:
        logger.error(f"Search failed. No results found for '{query}'")
    
    # Test court filtering
    court_code = "KESC"
    logger.info(f"Testing case retrieval for {court_code}...")
    
    court_cases = scraper.get_case_law(court_code, limit=5)
    
    if court_cases:
        logger.info(f"Court case retrieval successful! Found {len(court_cases)} cases from {court_code}")
        logger.info(f"First case: {court_cases[0].get('title', 'No title')}")
    else:
        logger.error(f"Court case retrieval failed. No cases found for {court_code}")
    
    # Test legislation retrieval
    logger.info("Testing legislation retrieval...")
    
    legislation = scraper.get_legislation(limit=5)
    
    if legislation:
        logger.info(f"Legislation retrieval successful! Found {len(legislation)} legislation items")
        logger.info(f"First legislation: {legislation[0].get('title', 'No title')}")
    else:
        logger.error("Legislation retrieval failed. No legislation found")
    
    return results, court_cases, legislation

def test_research_assistant():
    """Test the Legal Research Assistant"""
    logger.info("Testing Legal Research Assistant...")
    
    # Initialize research assistant
    research_assistant = LegalResearchAssistant()
    
    # Test legal issue research
    query = "defamation on social media"
    court_filters = ["KESC", "KECA"]
    
    logger.info(f"Researching issue: '{query}' with court filters: {court_filters}")
    
    results = research_assistant.research_legal_issue(query, court_filters)
    
    if results:
        logger.info("Research successful!")
        if 'results' in results:
            logger.info(f"Found {len(results['results'])} results")
        if 'analysis' in results:
            logger.info("Analysis was generated")
        
        # Save research to database
        with app.app_context():
            user_id = create_test_user()
            
            research_history = LegalResearch(
                title=f"Test Research: {query[:50]}",
                query=query,
                results=json.dumps(results),
                source="ai_research",
                court_filter=",".join(court_filters),
                result_count=len(results.get('results', [])),
                user_id=user_id
            )
            
            db.session.add(research_history)
            db.session.commit()
            logger.info(f"Saved research to database with ID: {research_history.id}")
    else:
        logger.error("Research failed. No results returned")
    
    return results

def test_document_analysis():
    """Test document analysis functionality"""
    logger.info("Testing document analysis...")
    
    # Initialize research assistant
    research_assistant = LegalResearchAssistant()
    
    # Test document to analyze
    document_text = """
    IN THE HIGH COURT OF KENYA AT NAIROBI
    COMMERCIAL AND TAX DIVISION
    CIVIL CASE NO. 123 OF 2023
    
    BETWEEN
    
    ABC COMPANY LIMITED...............................................PLAINTIFF
    
    AND
    
    XYZ CORPORATION LIMITED......................................DEFENDANT
    
    RULING
    
    1. The Plaintiff filed this suit seeking damages for breach of contract. The Defendant has raised a preliminary objection stating that the matter should be referred to arbitration as per the contract.
    
    2. The contract dated 1st January 2023 contains the following clause: "Any dispute arising out of or in connection with this contract shall be referred to and finally resolved by arbitration under the Rules of the Nairobi Centre for International Arbitration."
    
    3. Having considered the submissions of both parties, I find that the arbitration clause is valid and binding on the parties. Section 6 of the Arbitration Act requires the court to refer parties to arbitration where there is a valid arbitration agreement.
    
    4. Accordingly, the preliminary objection is upheld. The parties are hereby referred to arbitration as per the agreement. Costs in the cause.
    
    DATED and DELIVERED at NAIROBI this 15th day of March 2023.
    
    JUDGE
    """
    
    logger.info("Analyzing document...")
    
    analysis_results = research_assistant.analyze_legal_document(document_text)
    
    if analysis_results:
        logger.info("Document analysis successful!")
        logger.info(f"Document type identified as: {analysis_results.get('document_type', 'Unknown')}")
        
        # Save analysis to database
        with app.app_context():
            user_id = create_test_user()
            
            document_type = analysis_results.get('document_type', 'Unknown document')
            research_history = LegalResearch(
                title=f"Test Analysis: {document_type}",
                query=document_text[:200] + "...",
                results=json.dumps(analysis_results),
                source="ai_analysis",
                result_count=1,
                user_id=user_id
            )
            
            db.session.add(research_history)
            db.session.commit()
            logger.info(f"Saved document analysis to database with ID: {research_history.id}")
    else:
        logger.error("Document analysis failed. No results returned")
    
    return analysis_results

def run_all_tests():
    """Run all tests"""
    logger.info("=== STARTING LEGAL RESEARCH TESTS ===")
    
    search_results = test_search()
    logger.info("\n")
    
    research_results = test_research_assistant()
    logger.info("\n")
    
    analysis_results = test_document_analysis()
    logger.info("\n")
    
    logger.info("=== ALL TESTS COMPLETED ===")
    
    return {
        'search_results': search_results,
        'research_results': research_results,
        'analysis_results': analysis_results
    }

if __name__ == "__main__":
    run_all_tests()