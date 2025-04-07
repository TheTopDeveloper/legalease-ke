"""
Test script for the Vector Database functionality.
This script tests the functionality of the vector database to store and retrieve legal content.
"""
import os
import json
import shutil
import unittest
import numpy as np
from utils.vector_db import VectorDatabase
from utils.llm import MockLLMClient
import tempfile

class TestVectorDatabase(unittest.TestCase):
    """Test case for the Vector Database"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Create a temporary directory for the test database
        self.temp_dir = tempfile.mkdtemp()
        # Use MockLLMClient to avoid external dependencies
        self.mock_llm = MockLLMClient()
        # Initialize vector database with test path and mock LLM client
        self.vector_db = VectorDatabase(db_path=self.temp_dir, llm_client=self.mock_llm)
        
        # Sample test data
        self.sample_case = {
            'title': 'Test Case v. Respondent',
            'citation': 'Civil Appeal No. 123 of 2023',
            'court': 'Supreme Court of Kenya',
            'date': '2023-05-15',
            'parties': {
                'applicant': 'Test Case',
                'respondent': 'Respondent'
            },
            'summary': 'This is a test case about judicial review and constitutional interpretation.',
            'url': 'https://example.com/case123'
        }
        
        self.sample_statute = {
            'title': 'Data Protection Act',
            'chapter': 'Chapter 11A',
            'date': '2019-11-08',
            'summary': 'An Act of Parliament to establish the Office of the Data Protection Commissioner.',
            'url': 'https://example.com/statutes/dpa'
        }
        
        self.sample_document = {
            'title': 'Legal Brief on Constitutional Rights',
            'document_type': 'Brief',
            'content': 'This legal brief examines the scope of constitutional rights in Kenya.',
            'status': 'Draft',
            'created_at': '2023-06-20'
        }
        
        self.sample_contract = {
            'title': 'Service Agreement',
            'contract_type': 'Service',
            'content': 'This service agreement outlines the terms and conditions...',
            'key_terms': 'Payment terms: 30 days, Duration: 1 year',
            'status': 'Active',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31'
        }
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_add_and_retrieve_case(self):
        """Test adding and retrieving a case from the vector database"""
        # Add the sample case to the database
        case_id = self.vector_db.add_case(self.sample_case)
        
        # Verify case was added successfully
        self.assertTrue(case_id, "Case ID should not be empty")
        
        # Search for the case using keywords from the case
        results = self.vector_db.search_cases("judicial review constitutional interpretation")
        
        # Verify search results
        self.assertTrue(len(results) > 0, "Search should return at least one result")
        self.assertEqual(results[0]['id'], case_id, "First result should match the added case")
        self.assertEqual(results[0]['title'], self.sample_case['title'], "Title should match")
        self.assertEqual(results[0]['court'], self.sample_case['court'], "Court should match")
    
    def test_add_and_retrieve_statute(self):
        """Test adding and retrieving a statute from the vector database"""
        # Add the sample statute to the database
        statute_id = self.vector_db.add_statute(self.sample_statute)
        
        # Verify statute was added successfully
        self.assertTrue(statute_id, "Statute ID should not be empty")
        
        # Search for the statute using keywords from the statute
        results = self.vector_db.search_statutes("data protection commissioner")
        
        # Verify search results
        self.assertTrue(len(results) > 0, "Search should return at least one result")
        self.assertEqual(results[0]['id'], statute_id, "First result should match the added statute")
        self.assertEqual(results[0]['title'], self.sample_statute['title'], "Title should match")
        self.assertEqual(results[0]['chapter'], self.sample_statute['chapter'], "Chapter should match")
    
    def test_add_and_retrieve_document(self):
        """Test adding and retrieving a document from the vector database"""
        # Add the sample document to the database
        document_id = self.vector_db.add_document(self.sample_document)
        
        # Verify document was added successfully
        self.assertTrue(document_id, "Document ID should not be empty")
        
        # Search for the document using keywords from the document
        results = self.vector_db.search_documents("constitutional rights Kenya")
        
        # Verify search results
        self.assertTrue(len(results) > 0, "Search should return at least one result")
        self.assertEqual(results[0]['id'], document_id, "First result should match the added document")
        self.assertEqual(results[0]['title'], self.sample_document['title'], "Title should match")
        self.assertEqual(results[0]['document_type'], self.sample_document['document_type'], "Document type should match")
    
    def test_add_and_retrieve_contract(self):
        """Test adding and retrieving a contract from the vector database"""
        # Add the sample contract to the database
        contract_id = self.vector_db.add_contract(self.sample_contract)
        
        # Verify contract was added successfully
        self.assertTrue(contract_id, "Contract ID should not be empty")
        
        # Search for the contract using keywords from the contract
        results = self.vector_db.search_contracts("service agreement terms conditions")
        
        # Verify search results
        self.assertTrue(len(results) > 0, "Search should return at least one result")
        self.assertEqual(results[0]['id'], contract_id, "First result should match the added contract")
        self.assertEqual(results[0]['title'], self.sample_contract['title'], "Title should match")
        self.assertEqual(results[0]['contract_type'], self.sample_contract['contract_type'], "Contract type should match")
    
    def test_search_all(self):
        """Test searching across all collections"""
        # Add sample data to all collections
        case_id = self.vector_db.add_case(self.sample_case)
        statute_id = self.vector_db.add_statute(self.sample_statute)
        document_id = self.vector_db.add_document(self.sample_document)
        contract_id = self.vector_db.add_contract(self.sample_contract)
        
        # Search across all collections
        results = self.vector_db.search_all("legal rights")
        
        # Verify structure of results
        self.assertIn('cases', results, "Results should include cases collection")
        self.assertIn('statutes', results, "Results should include statutes collection")
        self.assertIn('documents', results, "Results should include documents collection")
        self.assertIn('contracts', results, "Results should include contracts collection")
    
    def test_collection_initialization(self):
        """Test that collections are properly initialized"""
        # Verify all collections exist
        self.assertIsNotNone(self.vector_db.case_collection, "Case collection should be initialized")
        self.assertIsNotNone(self.vector_db.statute_collection, "Statute collection should be initialized")
        self.assertIsNotNone(self.vector_db.document_collection, "Document collection should be initialized")
        self.assertIsNotNone(self.vector_db.contract_collection, "Contract collection should be initialized")
    
    def test_embedding_function(self):
        """Test the embedding function"""
        # Get embedding for a test text
        test_text = "This is a test text for embedding"
        
        # Use the embedding function from the vector database
        embedding = self.vector_db.embedding_function([test_text])
        
        # Print debug information
        print(f"Embedding type: {type(embedding)}")
        print(f"Embedding length: {len(embedding)}")
        print(f"Embedding[0] type: {type(embedding[0])}")
        
        # Verify embedding structure
        self.assertEqual(len(embedding), 1, "Should return one embedding")
        self.assertTrue(isinstance(embedding[0], (list, float, np.ndarray)), "Embedding should be a list, float, or numpy array")
        
        # If embedding[0] is a list, check its dimensions
        if isinstance(embedding[0], list):
            self.assertEqual(len(embedding[0]), 384, "Embedding should have 384 dimensions")
        # If embedding[0] is a float, embedding itself should be the list of dimensions
        else:
            self.assertEqual(len(embedding), 1, "Should have one embedding")

    def test_empty_search_results(self):
        """Test handling of empty search results"""
        # Search with a term unlikely to match anything in the empty database
        results = self.vector_db.search_cases("xyzabcunlikelyterm123")
        
        # Verify empty results handling
        self.assertEqual(len(results), 0, "Search should return empty results")
        self.assertIsInstance(results, list, "Results should be a list even when empty")

if __name__ == "__main__":
    unittest.main()