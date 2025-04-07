"""
Test script for the integration between scraper and vector database.
This script tests the workflow of scraping data and storing it in the vector database.
"""
import os
import shutil
import unittest
from unittest.mock import patch, MagicMock
import tempfile
import json

from utils.scraper import KenyaLawScraper
from utils.vector_db import VectorDatabase
from utils.llm import MockLLMClient

class TestScraperVectorDBIntegration(unittest.TestCase):
    """Test case for the integration between KenyaLawScraper and VectorDatabase"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create a temporary directory for the test database
        self.temp_dir = tempfile.mkdtemp()
        # Use MockLLMClient to avoid external dependencies
        self.mock_llm = MockLLMClient()
        # Initialize vector database with test path and mock LLM client
        self.vector_db = VectorDatabase(db_path=self.temp_dir, llm_client=self.mock_llm)
        
        # Create mock scraper with stubbed responses
        self.scraper = MagicMock()
        
        # Mock case data
        self.mock_case = {
            'title': 'Petitioner v. Attorney General [2023] eKLR',
            'full_text': 'This is a mock case about constitutional rights...',
            'citation': 'Petition No. 13 of 2023',
            'court': 'Supreme Court of Kenya',
            'judges': ['Justice A', 'Justice B', 'Justice C'],
            'date': '2023-04-15',
            'parties': {
                'applicant': 'Petitioner',
                'respondent': 'Attorney General'
            },
            'ruling': 'The Court finds that the constitutional rights were violated...',
            'url': 'https://example.com/case123'
        }
        
        # Mock statute data
        self.mock_statute = {
            'title': 'The Constitution of Kenya',
            'full_text': 'This is the supreme law of the Republic of Kenya...',
            'chapter': 'Chapter I - Sovereignty of the People and Supremacy of the Constitution',
            'date': '2010-08-27',
            'url': 'https://example.com/constitution'
        }
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    @patch('utils.scraper.KenyaLawScraper.get_case_details')
    def test_case_scraping_to_vector_db(self, mock_get_case_details):
        """Test scraping a case and storing it in the vector database"""
        # Configure mock to return sample case
        mock_get_case_details.return_value = self.mock_case
        
        # Create actual scraper instance for this test
        real_scraper = KenyaLawScraper()
        
        # Test the workflow
        # 1. Get case details from scraper (mocked)
        case_url = "https://example.com/case123"
        case_data = real_scraper.get_case_details(case_url)
        
        # Verify mock was called
        mock_get_case_details.assert_called_once_with(case_url)
        
        # 2. Store case in vector database
        case_id = self.vector_db.add_case(case_data)
        
        # Verify case ID is returned
        self.assertTrue(case_id, "Case ID should not be empty")
        
        # 3. Search for the case using relevant keywords
        search_results = self.vector_db.search_cases("constitutional rights")
        
        # Verify search returns the case
        self.assertTrue(len(search_results) > 0, "Search should return results")
        self.assertEqual(search_results[0]['id'], case_id, "Search result should match added case")
        self.assertEqual(search_results[0]['title'], self.mock_case['title'], "Title should match")
    
    def test_multiple_cases_batch_processing(self):
        """Test processing multiple cases in batch"""
        # Create multiple mock cases
        mock_cases = []
        for i in range(5):
            case = self.mock_case.copy()
            case['title'] = f"Case {i} v. Respondent [2023] eKLR"
            case['citation'] = f"Petition No. {i} of 2023"
            mock_cases.append(case)
        
        # Process each case and store in vector DB
        case_ids = []
        for case in mock_cases:
            case_id = self.vector_db.add_case(case)
            case_ids.append(case_id)
        
        # Verify all cases were added
        self.assertEqual(len(case_ids), len(mock_cases), "All cases should be added")
        
        # Test searches for different cases
        for i, case in enumerate(mock_cases):
            # Search using case number
            search_results = self.vector_db.search_cases(f"Petition No. {i}")
            self.assertTrue(len(search_results) > 0, f"Search for case {i} should return results")
            found_case = next((c for c in search_results if c['id'] == case_ids[i]), None)
            self.assertIsNotNone(found_case, f"Case {i} should be found in search results")
    
    def test_data_verification(self):
        """Test verifying the integrity of data stored in vector DB"""
        # Store a case in vector DB
        case_id = self.vector_db.add_case(self.mock_case)
        
        # Search for exact title match
        search_results = self.vector_db.search_cases(self.mock_case['title'])
        
        # Verify data integrity
        self.assertTrue(len(search_results) > 0, "Search should return results")
        result = search_results[0]
        
        # Check that metadata was preserved correctly
        self.assertEqual(result['title'], self.mock_case['title'], "Title should be preserved")
        self.assertEqual(result['citation'], self.mock_case['citation'], "Citation should be preserved")
        self.assertEqual(result['court'], self.mock_case['court'], "Court should be preserved")
        self.assertEqual(result['date'], self.mock_case['date'], "Date should be preserved")
    
    @patch('utils.scraper.KenyaLawScraper.get_case_law')
    @patch('utils.scraper.KenyaLawScraper.get_case_details')
    def test_end_to_end_scraping_workflow(self, mock_get_case_details, mock_get_case_law):
        """Test the end-to-end workflow from scraping multiple cases to searching"""
        # Configure mocks
        mock_case_listings = [
            {
                'title': 'Case 1 v. Respondent',
                'link': 'https://example.com/case1',
                'metadata': {'Date': '2023-01-01'}
            },
            {
                'title': 'Case 2 v. Respondent',
                'link': 'https://example.com/case2',
                'metadata': {'Date': '2023-02-01'}
            }
        ]
        mock_get_case_law.return_value = mock_case_listings
        
        # Configure case details mock to return different data based on URL
        def get_case_details_side_effect(url):
            if url == 'https://example.com/case1':
                case = self.mock_case.copy()
                case['title'] = 'Case 1 v. Respondent [2023] eKLR'
                case['citation'] = 'Petition No. 1 of 2023'
                case['ruling'] = 'This case concerns property rights...'
                return case
            elif url == 'https://example.com/case2':
                case = self.mock_case.copy()
                case['title'] = 'Case 2 v. Respondent [2023] eKLR'
                case['citation'] = 'Petition No. 2 of 2023'
                case['ruling'] = 'This case concerns freedom of expression...'
                return case
            return None
            
        mock_get_case_details.side_effect = get_case_details_side_effect
        
        # Create actual scraper instance for this test
        real_scraper = KenyaLawScraper()
        
        # 1. Get case listings
        cases = real_scraper.get_case_law('KESC', limit=2)
        self.assertEqual(len(cases), 2, "Should get 2 case listings")
        
        # 2. Process each case and store in vector DB
        case_ids = []
        for case_listing in cases:
            case_details = real_scraper.get_case_details(case_listing['link'])
            if case_details:
                case_id = self.vector_db.add_case(case_details)
                case_ids.append(case_id)
        
        self.assertEqual(len(case_ids), 2, "Both cases should be added to vector DB")
        
        # 3. Test search functionality
        property_search = self.vector_db.search_cases("property rights")
        self.assertTrue(len(property_search) > 0, "Property rights search should return results")
        
        freedom_search = self.vector_db.search_cases("freedom of expression")
        self.assertTrue(len(freedom_search) > 0, "Freedom of expression search should return results")
        
        # Verify different searches return different top results
        self.assertNotEqual(
            property_search[0]['id'],
            freedom_search[0]['id'],
            "Different searches should return different top results"
        )
    
    def test_vector_db_data_persistence(self):
        """Test that vector database persists data between instances"""
        # Store case in vector DB
        case_id = self.vector_db.add_case(self.mock_case)
        
        # Create a new instance pointing to same directory
        new_vector_db = VectorDatabase(db_path=self.temp_dir, llm_client=self.mock_llm)
        
        # Search for case in new instance
        search_results = new_vector_db.search_cases(self.mock_case['title'])
        
        # Verify data persistence
        self.assertTrue(len(search_results) > 0, "Search should return results")
        self.assertEqual(search_results[0]['id'], case_id, "Retrieved case ID should match original")
    
    def test_error_handling(self):
        """Test error handling in the integration workflow"""
        # Test handling of None response from scraper
        with patch('utils.scraper.KenyaLawScraper.get_case_details', return_value=None):
            real_scraper = KenyaLawScraper()
            case_data = real_scraper.get_case_details("https://example.com/nonexistent")
            self.assertIsNone(case_data, "Should handle None response gracefully")
        
        # Test vector database with incomplete data
        incomplete_case = {
            'title': 'Incomplete Case'
            # Missing other fields
        }
        case_id = self.vector_db.add_case(incomplete_case)
        self.assertTrue(case_id, "Should add case despite incomplete data")
        
        # Check that search still works
        search_results = self.vector_db.search_cases("Incomplete Case")
        self.assertTrue(len(search_results) > 0, "Should find incomplete case")

if __name__ == "__main__":
    unittest.main()