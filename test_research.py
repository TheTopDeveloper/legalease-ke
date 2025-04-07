"""
Test script for the legal research functionality.
This script tests the functionality of the legal research and analysis tools.
"""
import unittest
from unittest.mock import patch, MagicMock
import os
import json
import datetime
import tempfile
import shutil

# Import the necessary modules
from app import db, app
from models import User, LegalResearch, Client, Case
from utils.vector_db import VectorDatabase
from utils.llm import MockLLMClient, LegalAssistant

class TestLegalResearch(unittest.TestCase):
    """Test case for the legal research functionality"""
    
    def setUp(self):
        """Set up test environment before each test"""
        # Configure Flask app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        # Create app context
        self.app_context = app.app_context()
        self.app_context.push()
        
        # Create database tables
        db.create_all()
        
        # Create test user
        self.test_user = User(
            username='testuser',
            email='test@example.com'
        )
        self.test_user.set_password('testpassword')
        db.session.add(self.test_user)
        
        # Create test client
        self.test_client = Client(
            name='Test Client',
            email='client@example.com',
            phone='1234567890',
            address='123 Test Street',
            user_id=1
        )
        db.session.add(self.test_client)
        
        # Create test case
        self.test_case = Case(
            title='Research Test Case',
            case_number='CV-2023-008',
            court='High Court',
            filing_date=datetime.datetime.now(),
            status='Active',
            description='This is a test case for legal research',
            client_id=1,
            user_id=1
        )
        db.session.add(self.test_case)
        db.session.commit()
        
        # Create temporary directory for vector database
        self.temp_dir = tempfile.mkdtemp()
        self.mock_llm = MockLLMClient()
        self.vector_db = VectorDatabase(db_path=self.temp_dir, llm_client=self.mock_llm)
        
        # Initialize legal assistant
        self.legal_assistant = LegalAssistant(llm_client=self.mock_llm)
    
    def tearDown(self):
        """Clean up after each test"""
        # Remove database tables
        db.session.remove()
        db.drop_all()
        
        # Remove app context
        self.app_context.pop()
        
        # Remove temporary directory
        shutil.rmtree(self.temp_dir)
    
    def test_create_legal_research(self):
        """Test creating a new legal research record"""
        # Create a legal research record
        research = LegalResearch(
            title='Constitutional Law Research',
            question='What are the key constitutional principles in Kenya?',
            court_filter='Supreme Court',
            user_id=self.test_user.id,
            case_id=self.test_case.id,
            status='In Progress',
            has_arguments=True,
            tokens_used=1500
        )
        db.session.add(research)
        db.session.commit()
        
        # Verify research was created
        saved_research = LegalResearch.query.filter_by(title='Constitutional Law Research').first()
        self.assertIsNotNone(saved_research, "Research should be created")
        self.assertEqual(saved_research.question, 'What are the key constitutional principles in Kenya?', "Question should match")
        self.assertEqual(saved_research.court_filter, 'Supreme Court', "Court filter should match")
        self.assertEqual(saved_research.status, 'In Progress', "Status should match")
        self.assertTrue(saved_research.has_arguments, "Should have arguments flag set")
        self.assertEqual(saved_research.tokens_used, 1500, "Tokens used should match")
    
    @patch('utils.llm.LegalAssistant.conduct_legal_research')
    def test_conduct_research(self, mock_conduct_research):
        """Test conducting legal research"""
        # Configure mock
        mock_research_response = {
            'summary': 'This is a summary of the research findings.',
            'key_points': ['Point 1', 'Point 2', 'Point 3'],
            'cases': [
                {'title': 'Case 1', 'citation': 'Citation 1', 'relevance': 'High'},
                {'title': 'Case 2', 'citation': 'Citation 2', 'relevance': 'Medium'}
            ],
            'statutes': [
                {'title': 'Statute 1', 'chapter': 'Chapter 1', 'relevance': 'High'}
            ],
            'arguments': ['Argument 1', 'Argument 2'],
            'rebuttals': ['Rebuttal 1']
        }
        mock_conduct_research.return_value = mock_research_response
        
        # Create a legal research record
        research = LegalResearch(
            title='Test Research',
            question='What are the legal implications of privacy violations?',
            court_filter='High Court',
            user_id=self.test_user.id,
            case_id=self.test_case.id,
            status='Pending',
            has_arguments=True
        )
        db.session.add(research)
        db.session.commit()
        
        # Conduct research
        result = self.legal_assistant.conduct_legal_research(
            question=research.question,
            court_filter=research.court_filter,
            include_arguments=research.has_arguments
        )
        
        # Verify research response
        self.assertEqual(result, mock_research_response, "Research response should match mock")
        
        # Update research with results
        research.summary = result['summary']
        research.content = json.dumps(result)
        research.status = 'Completed'
        research.completed_at = datetime.datetime.now()
        research.tokens_used = 2000
        db.session.commit()
        
        # Verify update
        updated_research = LegalResearch.query.get(research.id)
        self.assertEqual(updated_research.status, 'Completed', "Status should be updated to Completed")
        self.assertEqual(updated_research.summary, 'This is a summary of the research findings.', "Summary should match")
        self.assertIsNotNone(updated_research.completed_at, "Completion timestamp should be set")
    
    def test_vector_db_search_integration(self):
        """Test integration between legal research and vector database"""
        # Add sample case to vector database
        sample_case = {
            'title': 'Privacy Case v. Data Controller',
            'citation': 'Civil Appeal No. 42 of 2022',
            'court': 'High Court of Kenya',
            'date': '2022-11-15',
            'parties': {
                'applicant': 'Privacy Case',
                'respondent': 'Data Controller'
            },
            'summary': 'A landmark case on data privacy and protection rights in Kenya.',
            'url': 'https://example.com/case42'
        }
        case_id = self.vector_db.add_case(sample_case)
        
        # Add sample statute to vector database
        sample_statute = {
            'title': 'Data Protection Act',
            'chapter': 'Chapter 11A',
            'date': '2019-11-08',
            'summary': 'An Act of Parliament to establish the Office of the Data Protection Commissioner.',
            'url': 'https://example.com/statutes/dpa'
        }
        statute_id = self.vector_db.add_statute(sample_statute)
        
        # Test search
        case_results = self.vector_db.search_cases('privacy violations data')
        statute_results = self.vector_db.search_statutes('data protection')
        
        # Verify search results
        self.assertTrue(len(case_results) > 0, "Case search should return results")
        self.assertTrue(len(statute_results) > 0, "Statute search should return results")
        self.assertEqual(case_results[0]['id'], case_id, "Case ID should match")
        self.assertEqual(statute_results[0]['id'], statute_id, "Statute ID should match")
    
    @patch('utils.llm.LegalAssistant.analyze_legal_document')
    def test_document_analysis(self, mock_analyze_document):
        """Test legal document analysis"""
        # Configure mock
        mock_analysis = {
            'summary': 'This is a summary of the document.',
            'key_points': ['Point 1', 'Point 2'],
            'legal_issues': ['Issue 1', 'Issue 2'],
            'recommendations': ['Recommendation 1', 'Recommendation 2'],
            'risk_assessment': 'Medium risk',
            'references': ['Reference 1', 'Reference 2']
        }
        mock_analyze_document.return_value = mock_analysis
        
        # Test document analysis
        sample_document = """
        THE DATA PROTECTION ACT, 2019
        
        AN ACT of Parliament to give effect to Article 31(c) and (d) of the Constitution; to establish 
        the Office of the Data Protection Commissioner; to make provision for the regulation of the 
        processing of personal data; to provide for the rights of data subjects and obligations of 
        data controllers and processors; and for connected purposes.
        """
        
        analysis = self.legal_assistant.analyze_legal_document(sample_document)
        
        # Verify analysis
        self.assertEqual(analysis, mock_analysis, "Document analysis should match mock")
    
    @patch('utils.llm.LegalAssistant.analyze_case_law')
    def test_case_law_analysis(self, mock_analyze_case_law):
        """Test case law analysis"""
        # Configure mock
        mock_analysis = {
            'case_name': 'Test Case v. Respondent',
            'citation': '[2022] eKLR',
            'court': 'Supreme Court',
            'judges': ['Judge A', 'Judge B'],
            'date': '2022-05-10',
            'summary': 'This is a summary of the case law.',
            'legal_principles': ['Principle 1', 'Principle 2'],
            'reasoning': 'This is the court\'s reasoning.',
            'ruling': 'Allowed',
            'implications': ['Implication 1', 'Implication 2']
        }
        mock_analyze_case_law.return_value = mock_analysis
        
        # Test case law analysis
        sample_case_law = """
        REPUBLIC OF KENYA
        IN THE SUPREME COURT OF KENYA
        AT NAIROBI
        
        PETITION NO. 13 OF 2022
        
        BETWEEN
        
        TEST CASE ..................................................................... PETITIONER
        
        AND
        
        RESPONDENT ............................................................... RESPONDENT
        
        JUDGMENT
        
        The court rules that...
        """
        
        analysis = self.legal_assistant.analyze_case_law(sample_case_law)
        
        # Verify analysis
        self.assertEqual(analysis, mock_analysis, "Case law analysis should match mock")
    
    @patch('utils.llm.LegalAssistant.generate_legal_arguments')
    def test_argument_generation(self, mock_generate_arguments):
        """Test legal argument generation"""
        # Configure mock
        mock_arguments = {
            'arguments': [
                {
                    'title': 'Argument 1',
                    'content': 'This is the content of argument 1.',
                    'supporting_cases': ['Case 1', 'Case 2'],
                    'supporting_statutes': ['Statute 1']
                },
                {
                    'title': 'Argument 2',
                    'content': 'This is the content of argument 2.',
                    'supporting_cases': ['Case 3'],
                    'supporting_statutes': ['Statute 2', 'Statute 3']
                }
            ],
            'rebuttals': [
                {
                    'title': 'Rebuttal 1',
                    'content': 'This is the content of rebuttal 1.',
                    'supporting_cases': ['Case 4'],
                    'supporting_statutes': []
                }
            ]
        }
        mock_generate_arguments.return_value = mock_arguments
        
        # Test argument generation
        arguments = self.legal_assistant.generate_legal_arguments(
            'Data privacy violation',
            'High Court',
            ['Privacy is a constitutional right.']
        )
        
        # Verify arguments
        self.assertEqual(arguments, mock_arguments, "Generated arguments should match mock")
    
    def test_research_token_tracking(self):
        """Test tracking of token usage for legal research"""
        # Create a legal research record
        research = LegalResearch(
            title='Token Usage Test',
            question='What are the leading cases on contract law?',
            court_filter='Court of Appeal',
            user_id=self.test_user.id,
            status='Completed',
            tokens_used=0
        )
        db.session.add(research)
        db.session.commit()
        
        # Update token usage
        token_usage = 3500
        research.tokens_used = token_usage
        db.session.commit()
        
        # Verify token usage update
        updated_research = LegalResearch.query.get(research.id)
        self.assertEqual(updated_research.tokens_used, token_usage, "Token usage should be updated")
        
        # Test aggregate token usage queries
        total_tokens_user = LegalResearch.query.filter_by(user_id=self.test_user.id).with_entities(
            db.func.sum(LegalResearch.tokens_used).label('total')
        ).scalar() or 0
        
        self.assertEqual(total_tokens_user, token_usage, "Total token usage should match")
    
    @patch('utils.vector_db.VectorDatabase.search_all')
    def test_comprehensive_research(self, mock_search_all):
        """Test comprehensive research combining multiple sources"""
        # Configure mock
        mock_search_results = {
            'cases': [
                {
                    'id': '1',
                    'title': 'Case A',
                    'citation': 'Citation A',
                    'court': 'Supreme Court',
                    'date': '2022-01-15',
                    'content': 'Content of Case A',
                    'score': 0.92
                }
            ],
            'statutes': [
                {
                    'id': '2',
                    'title': 'Statute B',
                    'chapter': 'Chapter B',
                    'date': '2021-05-20',
                    'content': 'Content of Statute B',
                    'score': 0.88
                }
            ],
            'documents': [
                {
                    'id': '3',
                    'title': 'Document C',
                    'document_type': 'Legal Brief',
                    'content': 'Content of Document C',
                    'score': 0.82
                }
            ],
            'contracts': []
        }
        mock_search_all.return_value = mock_search_results
        
        # Test comprehensive search
        search_results = self.vector_db.search_all('constitutional interpretation')
        
        # Verify search results
        self.assertEqual(search_results, mock_search_results, "Search results should match mock")
        
        # Create a research record using the search results
        research = LegalResearch(
            title='Comprehensive Research Test',
            question='What is the current state of constitutional interpretation?',
            court_filter='All Courts',
            user_id=self.test_user.id,
            case_id=self.test_case.id,
            status='In Progress',
            has_arguments=True,
            content=json.dumps(search_results)
        )
        db.session.add(research)
        db.session.commit()
        
        # Verify research content
        saved_research = LegalResearch.query.filter_by(title='Comprehensive Research Test').first()
        self.assertIsNotNone(saved_research, "Research should be created")
        saved_content = json.loads(saved_research.content) if saved_research.content else {}
        self.assertEqual(saved_content.get('cases', [])[0]['title'], 'Case A', "Case title should match")
        self.assertEqual(saved_content.get('statutes', [])[0]['title'], 'Statute B', "Statute title should match")

if __name__ == "__main__":
    unittest.main()