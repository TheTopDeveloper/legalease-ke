"""
Test script for the LLM functionality.
This script tests various LLM clients and their capabilities.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from utils.llm import (
    get_llm_client,
    MockLLMClient,
    OpenAIClient,
    OllamaClient,
    CounterCheckLLMClient,
    LegalAssistant
)

class TestLLMClients(unittest.TestCase):
    """Test case for the LLM clients"""
    
    def test_get_llm_client_fallback(self):
        """Test that get_llm_client falls back to MockLLMClient when Ollama is unavailable"""
        # Mock the environment without OpenAI API key and simulate Ollama connection failure
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
            with patch('requests.get', side_effect=Exception("Connection refused")):
                client = get_llm_client()
                self.assertIsInstance(client, MockLLMClient, "Client should be MockLLMClient when Ollama is unavailable")
    
    def test_mock_llm_client_generate(self):
        """Test MockLLMClient generate method"""
        client = MockLLMClient()
        
        # Test different prompt types
        case_response = client.generate("analyze this case")
        self.assertIn("Case Analysis", case_response, "Case analysis should be in response")
        
        document_response = client.generate("draft a legal document")
        self.assertIn("NOTICE OF APPEAL", document_response, "Document draft should be in response")
        
        statute_response = client.generate("analyze this statute")
        self.assertIn("Analysis of the Data Protection Act", statute_response, "Statute analysis should be in response")
        
        research_response = client.generate("conduct legal research")
        self.assertIn("LEGAL RESEARCH MEMORANDUM", research_response, "Legal research should be in response")
        
        summary_response = client.generate("provide a summary")
        self.assertIn("CASE SUMMARY", summary_response, "Case summary should be in response")
        
        contract_response = client.generate("draft a contract clause")
        self.assertIn("FORCE MAJEURE", contract_response, "Contract clause should be in response")
        
        generic_response = client.generate("random prompt")
        self.assertIn("mock response", generic_response, "Generic prompt should return mock response")
    
    def test_mock_llm_client_chat(self):
        """Test MockLLMClient chat method"""
        client = MockLLMClient()
        
        # Test chat with messages
        messages = [
            {"role": "system", "content": "You are a legal assistant."},
            {"role": "user", "content": "analyze this case"}
        ]
        
        response = client.chat(messages)
        self.assertIn("Case Analysis", response, "Chat response should process user message")
        
        # Test chat with empty messages
        empty_response = client.chat([])
        self.assertIn("mock response", empty_response, "Empty messages should return generic mock response")
    
    def test_mock_llm_client_embedding(self):
        """Test MockLLMClient embedding method"""
        client = MockLLMClient()
        
        # Get embedding for a test text
        embedding = client.get_embedding("This is a test")
        
        # Verify embedding structure
        self.assertEqual(len(embedding), 384, "Embedding should have 384 dimensions")
        self.assertTrue(all(-1 <= x <= 1 for x in embedding), "Embedding values should be between -1 and 1")
        
        # Test determinism - same input should give same output
        embedding2 = client.get_embedding("This is a test")
        self.assertEqual(embedding, embedding2, "Same input should give same embedding")
        
        # Different inputs should give different embeddings
        different_embedding = client.get_embedding("This is different")
        self.assertNotEqual(embedding, different_embedding, "Different inputs should give different embeddings")
    
    @patch('utils.llm.OpenAI')
    def test_openai_client(self, mock_openai):
        """Test OpenAIClient with mocked OpenAI API"""
        # Setup mock response
        mock_instance = MagicMock()
        mock_openai.return_value = mock_instance
        
        # Mock chat.completions.create response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OpenAI response"
        mock_instance.chat.completions.create.return_value = mock_response
        
        # Test with API key
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'mock-key'}):
            client = OpenAIClient()
            response = client.generate("Test prompt")
            
            self.assertEqual(response, "OpenAI response", "Should return mocked OpenAI response")
            mock_instance.chat.completions.create.assert_called_once()
    
    @patch('utils.llm.OpenAI')
    def test_openai_client_no_api_key(self, mock_openai):
        """Test OpenAIClient behavior when no API key is provided"""
        # Test without API key
        with patch.dict('os.environ', {'OPENAI_API_KEY': ''}):
            client = OpenAIClient()
            response = client.generate("Test prompt")
            
            self.assertIn("[OpenAI API key not configured", response, "Should return error message about missing API key")
            mock_openai.assert_not_called()
    
    @patch('requests.post')
    def test_ollama_client(self, mock_post):
        """Test OllamaClient with mocked requests"""
        # Setup mock response for generate
        mock_generate_response = MagicMock()
        mock_generate_response.json.return_value = {"response": "Ollama response"}
        mock_generate_response.raise_for_status = MagicMock()
        
        # Setup mock response for embeddings
        mock_embedding_response = MagicMock()
        mock_embedding_response.json.return_value = {"embedding": [0.1] * 384}
        mock_embedding_response.raise_for_status = MagicMock()
        
        # Setup mock response for chat
        mock_chat_response = MagicMock()
        mock_chat_response.json.return_value = {"message": {"content": "Ollama response"}}
        mock_chat_response.raise_for_status = MagicMock()
        
        # Alternate between mocked responses based on URL
        def side_effect(url, **kwargs):
            if url.endswith('/generate'):
                return mock_generate_response
            elif url.endswith('/embeddings'):
                return mock_embedding_response
            elif url.endswith('/chat'):
                return mock_chat_response
            return MagicMock()
            
        mock_post.side_effect = side_effect
        
        # Test client methods
        client = OllamaClient()
        
        # Test generate
        response = client.generate("Test prompt")
        self.assertEqual(response, "Ollama response", "Should return mocked Ollama response")
        
        # Test embeddings
        embedding = client.get_embedding("Test text")
        self.assertEqual(embedding, [0.1] * 384, "Should return mocked embedding")
        
        # Test chat
        chat_response = client.chat([{"role": "user", "content": "Test"}])
        self.assertEqual(chat_response, "Ollama response", "Should return mocked Ollama response for chat")
    
    @patch('requests.post')
    def test_ollama_client_error_handling(self, mock_post):
        """Test OllamaClient error handling with failed requests"""
        # Setup mock to raise an exception when called
        mock_post.side_effect = ConnectionError("Connection refused")
        
        # Test client methods with error handling
        client = OllamaClient()
        
        # Test generate with error
        response = client.generate("Test prompt")
        self.assertTrue(response.startswith("Error generating response"), "Should return error message")
        
        # Test embeddings with error
        embedding = client.get_embedding("Test text")
        self.assertEqual(embedding, [0.0] * 384, "Should return fallback embedding")
        
        # Test chat with error
        chat_response = client.chat([{"role": "user", "content": "Test"}])
        self.assertTrue(chat_response.startswith("Error generating response"), "Should return error message")
    
    def test_legal_assistant(self):
        """Test LegalAssistant with MockLLMClient"""
        # Initialize LegalAssistant with MockLLMClient
        mock_client = MockLLMClient()
        assistant = LegalAssistant(llm_client=mock_client)
        
        # Test analyze_case method
        case_text = "This is a sample case text."
        case_analysis = assistant.analyze_case(case_text)
        
        self.assertIsInstance(case_analysis, dict, "analyze_case should return a dictionary")
        self.assertIn('citation', case_analysis, "Analysis should include citation")
        self.assertIn('court', case_analysis, "Analysis should include court")
        self.assertIn('judges', case_analysis, "Analysis should include judges")
        
        # Test draft_legal_document method
        document = assistant.draft_legal_document(
            "Notice of Appeal",
            {"case": "Test Case", "court": "Supreme Court"},
            "Draft a notice of appeal for this case"
        )
        self.assertIn("NOTICE OF APPEAL", document, "Document should include the expected title")
        
        # Test analyze_statute method
        statute_text = "This is a sample statute text."
        statute_analysis = assistant.analyze_statute(statute_text)
        
        self.assertIsInstance(statute_analysis, dict, "analyze_statute should return a dictionary")
        self.assertIn('title', statute_analysis, "Analysis should include title")
        self.assertIn('enactment_date', statute_analysis, "Analysis should include enactment date")
        
        # Test generate_case_summary method
        summary = assistant.generate_case_summary("This is a sample case text.")
        self.assertIn("CASE SUMMARY", summary, "Summary should include the expected heading")
        
        # Test generate_contract_clause method
        clause = assistant.generate_contract_clause(
            "Service Agreement",
            "Force Majeure",
            "Standard force majeure clause"
        )
        self.assertIn("FORCE MAJEURE", clause, "Clause should include the expected heading")

    def test_extract_section(self):
        """Test the _extract_section method in LegalAssistant"""
        assistant = LegalAssistant(llm_client=MockLLMClient())
        
        # Test text with sections - ensure there's no additional processing of section labels
        test_text = """# Heading

Citation: ABC v. XYZ

Court: Supreme Court

Judges: Judge A, Judge B
"""
        
        citation = assistant._extract_section(test_text, "Citation:", "Court:")
        self.assertEqual(citation.strip(), "ABC v. XYZ", "Should extract citation section")
        
        court = assistant._extract_section(test_text, "Court:", "Judges:")
        self.assertEqual(court.strip(), "Supreme Court", "Should extract court section")
        
        # Test with numbered sections
        numbered_text = """
1. Citation: ABC v. XYZ
2. Court: Supreme Court
3. Judges: Judge A, Judge B
"""
        
        citation = assistant._extract_section(numbered_text, "1. Citation:", "2. Court:")
        self.assertEqual(citation.strip(), "ABC v. XYZ", "Should extract citation from numbered sections")
        
        # Test with final section
        judges = assistant._extract_section(test_text, "Judges:", "")
        self.assertEqual(judges.strip(), "Judge A, Judge B", "Should extract judges section as final section")

    @patch('utils.llm.OllamaClient')
    def test_counter_check_client(self, mock_ollama_client):
        """Test CounterCheckLLMClient with mocked OllamaClient"""
        # Setup mock responses for primary and secondary clients
        mock_primary = MagicMock()
        mock_secondary = MagicMock()
        
        # Configure the mock to return different instances for each call
        mock_ollama_client.side_effect = [mock_primary, mock_secondary]
        
        # Create CounterCheckLLMClient which will use our mocked clients
        client = CounterCheckLLMClient(
            primary_model="model1",
            secondary_model="model2"
        )
        
        # Verify the instances were created correctly
        self.assertEqual(client.primary_client, mock_primary)
        self.assertEqual(client.secondary_client, mock_secondary)
        
        # Test generate method with similar responses
        mock_primary.generate.return_value = "This is a test response."
        mock_secondary.generate.return_value = "This is a test answer."
        
        response = client.generate("Test prompt")
        mock_primary.generate.assert_called_once()
        mock_secondary.generate.assert_called_once()
        self.assertIn("This is a test response", response, "Should return primary client response")
        self.assertIn("Agreement between models:", response, "Should indicate agreement level")
        
        # Reset mocks for the next test
        mock_primary.reset_mock()
        mock_secondary.reset_mock()
        
        # Test generate method with very different responses
        mock_primary.generate.return_value = "The capital of Kenya is Nairobi."
        mock_secondary.generate.return_value = "The tallest mountain in Africa is Mount Kilimanjaro."
        
        response = client.generate("Test prompt")
        self.assertIn("The capital of Kenya is Nairobi", response, "Should return primary client response")
        self.assertIn("Agreement between models:", response, "Should indicate agreement level")
        
        # Test chat method
        mock_primary.chat.return_value = "This is a chat response."
        
        chat_response = client.chat([{"role": "user", "content": "Test"}])
        self.assertIn("This is a chat response", chat_response, "Should return primary client chat response")
        
        # Test get_embedding method (should pass through to primary client)
        mock_primary.get_embedding.return_value = [0.1, 0.2, 0.3]
        
        embedding = client.get_embedding("Test text")
        self.assertEqual(embedding, [0.1, 0.2, 0.3], "Should return primary client embedding")

if __name__ == "__main__":
    unittest.main()