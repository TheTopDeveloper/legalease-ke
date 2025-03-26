import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional
import config

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Define LLM models
LLM_MODELS = {
    "openai": {
        "default": "gpt-3.5-turbo",
        "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    },
    "ollama": {
        "default": "llama3",
        "models": ["llama3", "mistral", "deepseek", "gemma", "phi3", "mixtral"]
    }
}

def get_llm_client():
    """
    Get the appropriate LLM client based on available services
    
    Returns:
        A configured LLM client
    """
    # First try OpenAI if API key is available
    if OPENAI_AVAILABLE and os.environ.get("OPENAI_API_KEY"):
        logger.info("Using OpenAI client")
        return OpenAIClient()
    
    # Then try Ollama
    try:
        ollama_client = OllamaClient()
        # Test connection
        test_result = ollama_client.generate("Test connection", max_tokens=5)
        if test_result is not None:
            logger.info("Using Ollama client")
            return ollama_client
    except Exception as e:
        logger.warning(f"Ollama not available: {str(e)}")
    
    # Return OpenAI client even if not configured - it will handle its own errors
    logger.warning("No functioning LLM client available. Using unconfigured OpenAI client.")
    return OpenAIClient()

class OpenAIClient:
    """
    Client for interacting with OpenAI API
    """
    
    def __init__(self, api_key=None, model=None):
        """
        Initialize OpenAI client
        
        Args:
            api_key: OpenAI API key
            model: Default model to use
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model or "gpt-3.5-turbo"
        
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
            logger.info(f"Initialized OpenAI client with model: {self.model}")
    
    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate text completion using OpenAI
        
        Args:
            prompt: The prompt to generate a response for
            model: Model to use (defaults to configured model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        if not self.client:
            logger.error("OpenAI client not initialized. API key missing.")
            return None
            
        model = model or self.model
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a legal AI assistant for the Kenyan legal system."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {str(e)}")
            return None
    
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Get embedding vector for text using OpenAI
        
        Args:
            text: The text to get embedding for
            model: Model to use (defaults to embedding model)
            
        Returns:
            List of float values representing the embedding
        """
        if not self.client:
            logger.error("OpenAI client not initialized. API key missing.")
            return []
            
        embedding_model = model or "text-embedding-ada-002"
        
        try:
            response = self.client.embeddings.create(
                model=embedding_model,
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error getting embedding from OpenAI: {str(e)}")
            return []
    
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate chat completion using OpenAI
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            model: Model to use (defaults to configured model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response
        """
        if not self.client:
            logger.error("OpenAI client not initialized. API key missing.")
            return None
            
        model = model or self.model
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating chat response with OpenAI: {str(e)}")
            return None

class OllamaClient:
    """
    Client for interacting with OLLAMA LLM API
    """
    
    def __init__(self, base_url=None, model=None):
        """
        Initialize OLLAMA client
        
        Args:
            base_url: Base URL for OLLAMA API
            model: Default model to use
        """
        self.base_url = base_url or config.OLLAMA_BASE_URL
        self.model = model or config.OLLAMA_MODEL
        logger.info(f"Initialized OLLAMA client with base URL: {self.base_url}, model: {self.model}")
    
    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate text completion using OLLAMA
        
        Args:
            prompt: The prompt to generate a response for
            model: Model to use (defaults to configured model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        model = model or self.model
        
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            logger.debug(f"Sending request to OLLAMA: {url}, model: {model}")
            response = requests.post(url, json=payload, timeout=5)  # Add a 5 second timeout
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get("response", "")
            
            return generated_text
        
        except Exception as e:
            logger.error(f"Error generating text with OLLAMA: {str(e)}")
            # Return None instead of an error message to allow fallback handling
            return None
    
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Get embedding vector for text using OLLAMA
        
        Args:
            text: The text to get embedding for
            model: Model to use (defaults to configured model)
            
        Returns:
            List of float values representing the embedding
        """
        model = model or self.model
        
        try:
            url = f"{self.base_url}/api/embeddings"
            payload = {
                "model": model,
                "prompt": text
            }
            
            logger.debug(f"Getting embedding from OLLAMA: {url}, model: {model}")
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            embedding = result.get("embedding", [])
            
            return embedding
        
        except Exception as e:
            logger.error(f"Error getting embedding from OLLAMA: {str(e)}")
            return []

    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate chat completion using OLLAMA
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            model: Model to use (defaults to configured model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response
        """
        model = model or self.model
        
        try:
            url = f"{self.base_url}/api/chat"
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            logger.debug(f"Sending chat request to OLLAMA: {url}, model: {model}")
            response = requests.post(url, json=payload, timeout=5)  # Add a 5 second timeout
            response.raise_for_status()
            
            result = response.json()
            message = result.get("message", {})
            generated_text = message.get("content", "")
            
            return generated_text
        
        except Exception as e:
            logger.error(f"Error generating chat response with OLLAMA: {str(e)}")
            # Return None instead of an error message to allow fallback handling
            return None

class LegalAssistant:
    """
    Legal assistant using LLM for legal tasks
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize legal assistant
        
        Args:
            llm_client: LLM client (defaults to best available client)
        """
        self.llm_client = llm_client or get_llm_client()
    
    def analyze_case(self, case_text: str) -> Dict[str, Any]:
        """
        Analyze a legal case to extract key information
        
        Args:
            case_text: Full text of the case
            
        Returns:
            Dictionary with analysis results
        """
        prompt = f"""
        Please analyze the following Kenyan legal case and extract key information:
        
        {case_text[:5000]}... [truncated]
        
        Extract and organize the following information in a well-structured format:
        1. Case citation
        2. Court
        3. Judges
        4. Parties involved
        5. Key legal issues
        6. Main legal principles established
        7. Holding/Decision
        8. Reasoning
        9. Precedents cited
        10. Statutes/regulations referenced
        
        Format your response as a structured analysis that would be helpful for a legal professional.
        """
        
        response = self.llm_client.generate(prompt, temperature=0.1)
        
        # If LLM connection failed, return a default analysis with a notice
        if response is None:
            return {
                'full_analysis': "Unable to analyze case due to AI service unavailability. Please try again later.",
                'summary': "AI service unavailable",
                'legal_issues': "Unable to extract legal issues at this time",
                'legal_principles': "Unable to extract legal principles at this time",
                'decision': "Unable to extract decision at this time",
                'precedents_cited': "Unable to extract precedents at this time",
                'statutes_referenced': "Unable to extract statutes at this time"
            }
        
        # Attempt to extract structured information
        analysis = {
            'full_analysis': response,
            'summary': self._extract_section(response, 'summary', 'key legal issues'),
            'legal_issues': self._extract_section(response, 'key legal issues', 'main legal principles'),
            'legal_principles': self._extract_section(response, 'main legal principles', 'holding'),
            'decision': self._extract_section(response, 'holding', 'reasoning'),
            'precedents_cited': self._extract_section(response, 'precedents cited', 'statutes'),
            'statutes_referenced': self._extract_section(response, 'statutes', '')
        }
        
        return analysis
    
    def draft_legal_document(self, document_type: str, case_info: Dict[str, Any], instructions: str) -> str:
        """
        Draft a legal document based on provided information
        
        Args:
            document_type: Type of document to draft
            case_info: Information about the case
            instructions: Specific instructions for drafting
            
        Returns:
            Draft document text
        """
        prompt = f"""
        Please draft a Kenyan legal document of type: {document_type}
        
        Case Information:
        {json.dumps(case_info, indent=2)}
        
        Specific instructions:
        {instructions}
        
        Please follow Kenyan legal standards and formatting for this type of document. Include all necessary sections, references to appropriate laws and precedents, and proper legal language.
        """
        
        return self.llm_client.generate(prompt, temperature=0.2, max_tokens=2000)
    
    def analyze_statute(self, statute_text: str) -> Dict[str, Any]:
        """
        Analyze a statute to extract key information
        
        Args:
            statute_text: Full text of the statute
            
        Returns:
            Dictionary with analysis results
        """
        prompt = f"""
        Please analyze the following Kenyan statute and extract key information:
        
        {statute_text[:5000]}... [truncated]
        
        Extract and organize the following information:
        1. Full title of the statute
        2. Date of enactment
        3. Purpose and scope
        4. Key definitions
        5. Main provisions
        6. Obligations created
        7. Penalties or consequences
        8. Related regulations or statutory instruments
        
        Format your response as a structured analysis that would be helpful for a legal professional.
        """
        
        response = self.llm_client.generate(prompt, temperature=0.1)
        
        # If LLM connection failed, return a default analysis with a notice
        if response is None:
            return {
                'full_analysis': "Unable to analyze statute due to AI service unavailability. Please try again later.",
                'title': "AI service unavailable",
                'purpose': "Unable to extract purpose at this time",
                'key_definitions': "Unable to extract key definitions at this time",
                'main_provisions': "Unable to extract main provisions at this time",
                'obligations': "Unable to extract obligations at this time",
                'penalties': "Unable to extract penalties at this time"
            }
        
        # Attempt to extract structured information
        analysis = {
            'full_analysis': response,
            'title': self._extract_section(response, 'full title', 'date of enactment'),
            'purpose': self._extract_section(response, 'purpose and scope', 'key definitions'),
            'key_definitions': self._extract_section(response, 'key definitions', 'main provisions'),
            'main_provisions': self._extract_section(response, 'main provisions', 'obligations'),
            'obligations': self._extract_section(response, 'obligations', 'penalties'),
            'penalties': self._extract_section(response, 'penalties', 'related regulations')
        }
        
        return analysis
    
    def generate_legal_research_memo(self, topic: str, relevant_cases: List[Dict[str, Any]], relevant_statutes: List[Dict[str, Any]]) -> str:
        """
        Generate a legal research memorandum
        
        Args:
            topic: Research topic
            relevant_cases: List of relevant cases
            relevant_statutes: List of relevant statutes
            
        Returns:
            Legal research memorandum
        """
        cases_text = "\n\n".join([
            f"Case: {case.get('title', 'Untitled')}\nCitation: {case.get('citation', 'N/A')}\nSummary: {case.get('summary', 'No summary available')}"
            for case in relevant_cases
        ])
        
        statutes_text = "\n\n".join([
            f"Statute: {statute.get('title', 'Untitled')}\nSummary: {statute.get('summary', 'No summary available')}"
            for statute in relevant_statutes
        ])
        
        prompt = f"""
        Please draft a comprehensive legal research memorandum on the following topic under Kenyan law:
        
        TOPIC: {topic}
        
        RELEVANT CASES:
        {cases_text}
        
        RELEVANT STATUTES:
        {statutes_text}
        
        The memorandum should include:
        1. Introduction and Statement of the Legal Issue
        2. Brief Statement of the Conclusion
        3. Statement of Facts (synthesized from the available information)
        4. Discussion of Applicable Law
           a. Relevant statutory provisions
           b. Relevant case law
           c. Analysis of how the law applies to the facts
        5. Conclusion and Recommendations
        
        Please format this as a professional legal memorandum following Kenyan legal standards.
        """
        
        return self.llm_client.generate(prompt, temperature=0.3, max_tokens=3000)
    
    def generate_case_summary(self, case_text: str) -> str:
        """
        Generate a concise summary of a legal case
        
        Args:
            case_text: Full text of the case
            
        Returns:
            Concise case summary
        """
        prompt = f"""
        Please provide a concise summary of the following Kenyan legal case:
        
        {case_text[:5000]}... [truncated]
        
        Your summary should include:
        1. The case citation
        2. The parties involved
        3. The court that decided the case
        4. The key facts
        5. The legal issue(s) presented
        6. The court's holding
        7. The key reasoning
        8. The significance of the decision
        
        Limit your summary to approximately 300-500 words.
        """
        
        return self.llm_client.generate(prompt, temperature=0.2, max_tokens=800)
    
    def generate_contract_clause(self, contract_type: str, clause_purpose: str, specific_requirements: str) -> str:
        """
        Generate a contract clause based on provided requirements
        
        Args:
            contract_type: Type of contract
            clause_purpose: Purpose of the clause
            specific_requirements: Specific requirements for the clause
            
        Returns:
            Generated contract clause
        """
        prompt = f"""
        Please draft a legal clause for a {contract_type} contract under Kenyan law.
        
        PURPOSE OF THE CLAUSE: {clause_purpose}
        
        SPECIFIC REQUIREMENTS:
        {specific_requirements}
        
        The clause should:
        1. Be legally sound under Kenyan contract law
        2. Use precise and unambiguous language
        3. Address the specific purpose and requirements provided
        4. Follow standard legal drafting conventions
        5. Be enforceable in Kenyan courts
        
        Draft only the specific clause, not the entire contract.
        """
        
        return self.llm_client.generate(prompt, temperature=0.3, max_tokens=800)
    
    def _extract_section(self, text: str, section_start: str, section_end: str) -> str:
        """
        Extract a section from text between markers
        
        Args:
            text: Full text
            section_start: Start marker
            section_end: End marker
            
        Returns:
            Extracted section
        """
        # Case insensitive search
        text_lower = text.lower()
        start_pos = text_lower.find(section_start.lower())
        
        if start_pos == -1:
            return ""
        
        # Find the actual start of content after the header
        content_start = text.find(":", start_pos)
        if content_start == -1:
            content_start = start_pos + len(section_start)
        else:
            content_start += 1
        
        # Find the end position
        if section_end:
            end_pos = text_lower.find(section_end.lower(), content_start)
            if end_pos == -1:
                section = text[content_start:]
            else:
                section = text[content_start:end_pos]
        else:
            section = text[content_start:]
        
        return section.strip()
