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
        "default": config.OLLAMA_PRIMARY_MODEL,
        "models": [
            "llama3:latest", 
            "deepseek:latest", 
            "mistral", 
            "gemma", 
            "phi3", 
            "mixtral"
        ]
    }
}

class MockLLMClient:
    """
    Mock LLM client that provides reasonable responses without requiring an actual LLM.
    This is useful when Ollama is not available but we still want the application to function.
    """
    
    def __init__(self):
        """Initialize mock client"""
        logger.info("Initialized Mock LLM client (fallback responses)")
    
    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate a mock response based on the type of prompt
        
        Args:
            prompt: The prompt to generate a response for
            model: Ignored in mock client
            temperature: Ignored in mock client
            max_tokens: Ignored in mock client
            
        Returns:
            A reasonable mock response
        """
        # Check the type of prompt to provide an appropriate mock response
        prompt_lower = prompt.lower()
        
        if "analyze" in prompt_lower and "case" in prompt_lower:
            return self._mock_case_analysis()
        elif "draft" in prompt_lower and "document" in prompt_lower:
            return self._mock_document_draft()
        elif "analyze" in prompt_lower and "statute" in prompt_lower:
            return self._mock_statute_analysis()
        elif "legal research" in prompt_lower:
            return self._mock_legal_research()
        elif "summary" in prompt_lower:
            return self._mock_case_summary()
        elif "contract" in prompt_lower and "clause" in prompt_lower:
            return self._mock_contract_clause()
        else:
            # Generic response for other prompts
            return "[This is a mock response as the LLM service is currently unavailable. Please ensure Ollama server is running and properly configured if you need AI-generated responses.]"
    
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate a mock chat response
        
        Args:
            messages: List of message objects (used to extract the last user message)
            model: Ignored in mock client
            temperature: Ignored in mock client
            max_tokens: Ignored in mock client
            
        Returns:
            A reasonable mock response
        """
        # Extract the last user message if available
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        if user_messages:
            last_user_message = user_messages[-1].get('content', '')
            return self.generate(last_user_message)
        
        return "[This is a mock response as the LLM service is currently unavailable. Please ensure Ollama server is running and properly configured if you need AI-generated responses.]"
    
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Generate a mock embedding
        
        Args:
            text: The text to get embedding for
            model: Ignored in mock client
            
        Returns:
            A mock embedding vector with 384 dimensions (common embedding size)
        """
        # Generate a deterministic but seemingly random embedding based on the text
        import hashlib
        
        # Get a hash of the text
        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()
        
        # Use the hash to seed a random number generator
        import random
        random.seed(hash_bytes)
        
        # Generate a 384-dimension embedding with values between -1 and 1
        return [random.uniform(-1, 1) for _ in range(384)]
    
    def _mock_case_analysis(self) -> str:
        """Generate a mock case analysis"""
        return """# Case Analysis

## Case Citation
Civil Appeal No. 123 of 2022

## Court
Supreme Court of Kenya

## Judges
- Justice X (presiding)
- Justice Y
- Justice Z

## Parties Involved
Appellant: Company ABC Ltd.
Respondent: Company XYZ Ltd.

## Key Legal Issues
1. Whether the contract between the parties was validly terminated
2. Whether the appellant is entitled to damages for breach of contract

## Main Legal Principles Established
1. A party seeking to terminate a contract must show that the breach was fundamental
2. Notice of termination must be clear and unequivocal

## Holding/Decision
Appeal dismissed with costs to the respondent

## Reasoning
The Court found that the appellant had failed to demonstrate that the respondent's breach was fundamental. The Court also found that the termination notice was defective.

## Precedents Cited
1. Giella v. Cassman Brown & Co Ltd [1973] EA 358
2. East African Portland Cement Co. Ltd v. Ndung'u & Another, Civil Appeal No. 157 of 2011

## Statutes/Regulations Referenced
1. Law of Contract Act, Cap 23 Laws of Kenya
2. Civil Procedure Act, Cap 21 Laws of Kenya

[This is a mock analysis as the LLM service is currently unavailable]
"""
    
    def _mock_document_draft(self) -> str:
        """Generate a mock legal document draft"""
        return """# NOTICE OF APPEAL

IN THE SUPREME COURT OF KENYA AT NAIROBI
CIVIL APPEAL NO. _____ OF 2025

BETWEEN

ABC LIMITED................................................APPELLANT

AND

XYZ LIMITED...............................................RESPONDENT

(Being an appeal from the judgment of the Court of Appeal at Nairobi (Justice A, Justice B, and Justice C) dated 1st March, 2025 in Civil Appeal No. 100 of 2024)

TAKE NOTICE that ABC Limited, the Appellant herein, being dissatisfied with the decision of the Court of Appeal given at Nairobi on the 1st day of March, 2025, intends to appeal to the Supreme Court against the whole of the said decision.

DATED at Nairobi this _______ day of ________, 2025

SIGNED: ______________________
ADVOCATE FOR THE APPELLANT

DRAWN & FILED BY:
ABC ADVOCATES
Advocates for the Appellant
Address for Service:
P.O. Box 12345-00100
NAIROBI

TO: The Registrar
     Supreme Court of Kenya

AND TO: XYZ Advocates
         Advocates for the Respondent
         P.O. Box 54321-00100
         NAIROBI

[This is a mock document as the LLM service is currently unavailable]
"""
    
    def _mock_statute_analysis(self) -> str:
        """Generate a mock statute analysis"""
        return """# Analysis of the Data Protection Act, 2019

## Full Title of the Statute
The Data Protection Act, No. 24 of 2019, Laws of Kenya

## Date of Enactment
November 8, 2019

## Purpose and Scope
The Act aims to establish the legal and institutional framework for protecting personal data and to regulate the collection, processing, storage, use, and disclosure of personal data.

## Key Definitions
1. "Data controller" - a person who determines the purpose and means of processing personal data
2. "Data processor" - a person who processes personal data on behalf of a data controller
3. "Personal data" - any information relating to an identified or identifiable natural person (data subject)

## Main Provisions
1. Establishes the Office of the Data Protection Commissioner
2. Outlines registration requirements for data controllers and processors
3. Sets forth data protection principles
4. Provides for rights of data subjects
5. Establishes procedures for complaints, investigations, and enforcement

## Obligations Created
1. Data controllers must implement appropriate technical and organizational measures
2. Mandatory registration for data controllers and processors
3. Requirement to conduct data protection impact assessments for high-risk processing
4. Obligation to notify data breaches to the Commissioner

## Penalties or Consequences
1. General penalty: fine not exceeding five million shillings or imprisonment for a term not exceeding ten years, or both
2. Administrative fines up to five million shillings or 1% of annual turnover, whichever is lower

## Related Regulations or Statutory Instruments
1. Data Protection (Registration of Data Controllers and Data Processors) Regulations, 2021
2. Data Protection (Complaints Handling Procedure and Enforcement) Regulations, 2021

[This is a mock analysis as the LLM service is currently unavailable]
"""
    
    def _mock_legal_research(self) -> str:
        """Generate a mock legal research memo"""
        return """# LEGAL RESEARCH MEMORANDUM

## INTRODUCTION AND STATEMENT OF THE LEGAL ISSUE

This memorandum addresses the legal implications of electronic signatures in commercial contracts under Kenyan law. Specifically, this research examines whether electronic signatures are legally binding for commercial contracts in Kenya, and what requirements must be met for such signatures to be valid.

## BRIEF STATEMENT OF THE CONCLUSION

Electronic signatures are legally binding for commercial contracts in Kenya under the Kenya Information and Communications Act (KICA) and its amendments. To be valid, electronic signatures must meet certain criteria including authentication, reliability, and consent of the parties to use electronic form for the transaction.

## STATEMENT OF FACTS

Our client, ABC Ltd., is entering into several commercial agreements with both local and international business partners. They want to streamline their contract execution process by using electronic signature platforms. They need clarity on the legal standing of such signatures in Kenya.

## DISCUSSION OF APPLICABLE LAW

### Relevant Statutory Provisions

The primary legislation governing electronic signatures in Kenya is the Kenya Information and Communications Act (KICA), Cap 411A, particularly as amended by the Kenya Information and Communications (Amendment) Act of 2008. Section 83P of KICA recognizes electronic signatures and provides that where a law requires a signature, an electronic signature may satisfy that requirement.

### Relevant Case Law

In Musikari Kombo v. Royal Media Services Ltd [2018] eKLR, the court held that electronic signatures are valid where the method used is as reliable as appropriate for the purpose for which the information was communicated.

## CONCLUSION AND RECOMMENDATIONS

Electronic signatures are legally binding for commercial contracts in Kenya, provided they meet the requirements set forth in KICA. We recommend that ABC Ltd. implement an electronic signature system that:

1. Uniquely identifies the signatory
2. Maintains a clear audit trail of the signing process
3. Ensures the signatory intends to be bound by the signature
4. Obtains express consent from all parties to use electronic signatures

[This is a mock memorandum as the LLM service is currently unavailable]
"""
    
    def _mock_case_summary(self) -> str:
        """Generate a mock case summary"""
        return """# CASE SUMMARY: Mutual Benefits Assurance PLC v. KRA [2020] eKLR

## Citation
Civil Appeal No. 263 of 2019

## Parties Involved
Appellant: Mutual Benefits Assurance PLC
Respondent: Kenya Revenue Authority (KRA)

## Court
Court of Appeal of Kenya at Nairobi

## Key Facts
The appellant, an insurance company, disputed tax assessments issued by the KRA regarding withholding tax on reinsurance premiums paid to non-resident reinsurers between 2009-2015. The appellant argued that the Double Taxation Agreement (DTA) between Kenya and the respective countries of the reinsurers exempted them from withholding tax obligations.

## Legal Issues Presented
1. Whether reinsurance premiums paid to non-resident reinsurers are subject to withholding tax in Kenya
2. Whether the appellant can rely on DTAs to claim exemption from withholding tax

## Court's Holding
The Court held that reinsurance premiums paid to non-resident reinsurers are subject to withholding tax under Section 10 of the Income Tax Act unless specifically exempted under a DTA. The Court found that the appellant failed to provide evidence that the reinsurers were residents of countries with applicable DTAs with Kenya.

## Key Reasoning
The Court reasoned that while DTAs may provide exemptions from withholding tax, a taxpayer seeking to rely on such exemptions must provide satisfactory evidence of the residence status of the foreign entity. The appellant's failure to provide such evidence was fatal to its case.

## Significance of the Decision
This decision clarifies the application of withholding tax on reinsurance premiums and establishes the procedural requirements for claiming exemptions under DTAs. It emphasizes the importance of proper documentation when dealing with international tax matters.

[This is a mock summary as the LLM service is currently unavailable]
"""
    
    def _mock_contract_clause(self) -> str:
        """Generate a mock contract clause"""
        return """## FORCE MAJEURE CLAUSE

### 15. FORCE MAJEURE

15.1 Definition. For purposes of this Agreement, "Force Majeure" means an event or circumstance that is beyond the reasonable control of a Party, which event or circumstance was not reasonably foreseeable by such Party at the time of execution of this Agreement, and which prevents or delays a Party from performing its obligations under this Agreement, in whole or in part.

15.2 Suspension of Obligations. Neither Party shall be liable for any failure to perform or delay in performance of its obligations under this Agreement to the extent that and for so long as such failure or delay is caused by a Force Majeure event, provided that the Party affected by the Force Majeure event:

   (a) promptly notifies the other Party in writing of the nature and extent of the Force Majeure event;
   
   (b) could not have prevented or overcome the Force Majeure event by taking precautions which, having regard to all matters known to it before the occurrence of the Force Majeure event and all relevant factors, it ought reasonably to have taken;
   
   (c) has used reasonable endeavors to mitigate the effect of the Force Majeure event and to carry out its obligations under this Agreement in any other way that is reasonably practicable; and
   
   (d) resumes performance of its obligations as soon as reasonably possible after the Force Majeure event ceases.

15.3 Extended Force Majeure. If a Force Majeure event prevails for a continuous period in excess of ninety (90) days, the Parties shall enter into good faith discussions with a view to alleviating its effects, or to agreeing upon such alternative arrangements as may be fair and reasonable in the circumstances.

15.4 Termination for Extended Force Majeure. If a Force Majeure event prevents a Party from performing substantially all of its obligations under this Agreement for a continuous period of one hundred and eighty (180) days or more, the Party not affected by such event shall have the right to terminate this Agreement by giving thirty (30) days' written notice to the affected Party, without liability to either Party.

[This is a mock clause as the LLM service is currently unavailable]
"""


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
    
    # Create a MockLLMClient if Ollama is not available but still allow application to function
    mock_client = MockLLMClient()
    
    # Then try Ollama with counter-checking if enabled
    try:
        # List of potential Ollama API endpoints to check
        endpoints_to_check = [
            "/api/version",  # Standard version endpoint
            "/",             # Root endpoint (some Ollama versions respond here)
            "/api",          # API root
            "/v1/models",    # OpenAI-compatible endpoint some versions support
        ]
        
        # Log the configured Ollama URL for debugging
        logger.info(f"Attempting to connect to Ollama at base URL: {config.OLLAMA_BASE_URL}")
        
        ollama_detected = False
        for endpoint in endpoints_to_check:
            try:
                url = f"{config.OLLAMA_BASE_URL}{endpoint}"
                logger.info(f"Testing Ollama API endpoint: {url}")
                response = requests.get(url, timeout=2)
                status = response.status_code
                logger.info(f"Response from {url}: status code {status}")
                
                if status < 400:  # Any non-error response means the server is up
                    logger.info(f"Ollama server detected at {url} (status: {status})")
                    ollama_detected = True
                    break
            except Exception as e:
                logger.warning(f"Endpoint {url} not available: {str(e)}")
        
        if not ollama_detected:
            logger.warning(f"Ollama server not available at {config.OLLAMA_BASE_URL} - tried multiple endpoints")
            logger.info("Using Mock LLM client instead")
            return mock_client
        
        if config.ENABLE_LLM_COUNTERCHECK:
            # Create counter-check client with primary and secondary models
            counter_client = CounterCheckLLMClient(
                primary_model=config.OLLAMA_PRIMARY_MODEL,
                secondary_model=config.OLLAMA_SECONDARY_MODEL
            )
            # Test connection with reduced timeout
            try:
                test_result = counter_client.generate("Test", max_tokens=5)
                if test_result is not None:
                    logger.info("Using Counter-Check LLM client with multiple models")
                    return counter_client
            except Exception as e:
                logger.warning(f"Counter-Check client failed: {str(e)}")
                # Fall through to try regular client
        
        # Use regular Ollama client with primary model only
        ollama_client = OllamaClient()
        # Test connection with reduced timeout
        try:
            test_result = ollama_client.generate("Test", max_tokens=5)
            if test_result is not None:
                logger.info("Using Ollama client with single model")
                return ollama_client
        except Exception as e:
            logger.warning(f"Ollama client failed: {str(e)}")
            # Fall through to mock client
    except Exception as e:
        logger.warning(f"Ollama setup failed: {str(e)}")
    
    # Return MockLLMClient that provides reasonable fallback responses
    logger.info("Using Mock LLM client for fallback responses")
    return mock_client


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
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.model = model or "gpt-4o"  
        self.embedding_model = "text-embedding-3-small"
        
        if not self.api_key:
            logger.warning("No OpenAI API key provided. Set OPENAI_API_KEY environment variable.")
            self.client = None
        else:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info(f"Initialized OpenAI client with model: {self.model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.client = None
    
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
            return "[OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.]"
            
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
            return f"[Error generating text with OpenAI: {str(e)}]"
    
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
            
        # Use the latest text-embedding-3-small model (released after knowledge cutoff)
        embedding_model = model or self.embedding_model
        
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
            return "[OpenAI API key not configured. Please set the OPENAI_API_KEY environment variable.]"
            
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
            return f"[Error generating chat response with OpenAI: {str(e)}]"


class CounterCheckLLMClient:
    """
    Client for counter-checking responses between two different LLM models.
    This client uses two Ollama models to generate responses and verifies they're consistent.
    """
    
    def __init__(self, base_url=None, primary_model=None, secondary_model=None):
        """
        Initialize counter-check client with two model instances
        
        Args:
            base_url: Base URL for OLLAMA API
            primary_model: Primary model to use for generation
            secondary_model: Secondary model to use for verification
        """
        # Import config here to avoid potential scope issues
        import config as config_module
        self.base_url = base_url or config_module.OLLAMA_BASE_URL
        self.primary_model = primary_model or config_module.OLLAMA_PRIMARY_MODEL
        self.secondary_model = secondary_model or config_module.OLLAMA_SECONDARY_MODEL
        
        # Create two OllamaClient instances, one for each model
        self.primary_client = OllamaClient(base_url=self.base_url, model=self.primary_model)
        self.secondary_client = OllamaClient(base_url=self.base_url, model=self.secondary_model)
        
        logger.info(f"Initialized CounterCheck client with models: {self.primary_model} (primary) and {self.secondary_model} (secondary)")
    
    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate text completion using both models and counter-check results
        
        Args:
            prompt: The prompt to generate a response for
            model: Override model (will still use both for checking, but return this one's response)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text with confidence note
        """
        # Use specified model if provided, otherwise use primary
        preferred_model = model or self.primary_model
        
        # Generate responses from both models
        primary_response = self.primary_client.generate(
            prompt=prompt, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        
        secondary_response = self.secondary_client.generate(
            prompt=prompt, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        
        # If either model fails, return the successful one
        if primary_response is None and secondary_response is None:
            logger.error("Both LLM models failed to generate responses")
            return "[Error: Both LLM models failed to generate responses]"
        
        if primary_response is None:
            logger.warning(f"Primary model ({self.primary_model}) failed, using secondary model response")
            return f"{secondary_response}\n\n[Generated using only {self.secondary_model} due to primary model failure]"
        
        if secondary_response is None:
            logger.warning(f"Secondary model ({self.secondary_model}) failed, using primary model response")
            return f"{primary_response}\n\n[Generated using only {self.primary_model} due to secondary model failure]"
        
        # Compare responses to calculate agreement
        agreement_score = self._calculate_agreement(primary_response, secondary_response)
        
        # Add information about the counter-check in a footer
        confidence_note = f"\n\n[Agreement between models: {agreement_score:.0%}]"
        
        # Return the preferred model's response with the confidence note
        if preferred_model == self.primary_model:
            return primary_response + confidence_note
        else:
            return secondary_response + confidence_note
    
    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """
        Generate chat completion using both models and counter-check results
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            model: Override model (will still use both for checking, but return this one's response)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response with confidence note
        """
        # Use specified model if provided, otherwise use primary
        preferred_model = model or self.primary_model
        
        # Generate responses from both models
        primary_response = self.primary_client.chat(
            messages=messages, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        
        secondary_response = self.secondary_client.chat(
            messages=messages, 
            temperature=temperature, 
            max_tokens=max_tokens
        )
        
        # If either model fails, return the successful one
        if primary_response is None and secondary_response is None:
            logger.error("Both LLM models failed to generate responses")
            return "[Error: Both LLM models failed to generate responses]"
        
        if primary_response is None:
            logger.warning(f"Primary model ({self.primary_model}) failed, using secondary model response")
            return f"{secondary_response}\n\n[Generated using only {self.secondary_model} due to primary model failure]"
        
        if secondary_response is None:
            logger.warning(f"Secondary model ({self.secondary_model}) failed, using primary model response")
            return f"{primary_response}\n\n[Generated using only {self.primary_model} due to secondary model failure]"
        
        # Compare responses to calculate agreement
        agreement_score = self._calculate_agreement(primary_response, secondary_response)
        
        # Add information about the counter-check in a footer
        confidence_note = f"\n\n[Agreement between models: {agreement_score:.0%}]"
        
        # Return the preferred model's response with the confidence note
        if preferred_model == self.primary_model:
            return primary_response + confidence_note
        else:
            return secondary_response + confidence_note
    
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Get embedding vector for text
        
        Args:
            text: The text to get embedding for
            model: Model to use (defaults to primary model)
            
        Returns:
            List of float values representing the embedding
        """
        # For embeddings, just use the primary model
        return self.primary_client.get_embedding(text, model)
    
    def _calculate_agreement(self, text1: str, text2: str) -> float:
        """
        Calculate similarity/agreement between two text responses
        
        Args:
            text1: First text response
            text2: Second text response
            
        Returns:
            Float value between 0.0 and 1.0 representing agreement
        """
        # Simple string similarity based on word overlap for now
        # Could be improved with embedding-based similarity in future
        
        # Normalize texts: lowercase, remove punctuation
        def normalize(text):
            # Remove common punctuation and lowercase
            for char in '.,;:!?"\'()[]{}':
                text = text.replace(char, ' ')
            return text.lower()
        
        words1 = set(normalize(text1).split())
        words2 = set(normalize(text2).split())
        
        # Calculate Jaccard similarity: intersection over union
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        if union == 0:  # Avoid division by zero
            return 0.0
            
        return intersection / union


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
        # Import config here to avoid potential scope issues
        import config as config_module
        self.base_url = base_url or config_module.OLLAMA_BASE_URL
        self.model = model or config_module.OLLAMA_PRIMARY_MODEL
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
            Generated text or error message
        """
        model = model or self.model
        
        # Get Ollama version to determine which endpoints to prioritize
        # Import config here to avoid potential scope issues
        import config as config_module
        ollama_version = config_module.OLLAMA_VERSION
        logger.info(f"Using Ollama version: {ollama_version}")
        
        # Configure API endpoints based on Ollama version
        # For version 0.6.x, prioritize standard endpoints
        if ollama_version.startswith("0.6"):
            api_configs = [
                # Standard Ollama API for 0.6.x - primary endpoint for text generation
                {
                    "url": f"{self.base_url}/api/generate",
                    "payload": {
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    "extract": lambda data: data.get("response", "")
                },
                # Chat API for 0.6.x - alternative endpoint
                {
                    "url": f"{self.base_url}/api/chat",
                    "payload": {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    "extract": lambda data: data.get("message", {}).get("content", "")
                }
            ]
        else:
            # For other versions, try a broader range of endpoints
            api_configs = [
                # Standard Ollama API
                {
                    "url": f"{self.base_url}/api/generate",
                    "payload": {
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    "extract": lambda data: data.get("response", "")
                },
                # Newer Ollama chat API
                {
                    "url": f"{self.base_url}/api/chat",
                    "payload": {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    "extract": lambda data: data.get("message", {}).get("content", "")
                },
                # OpenAI-compatible endpoint (newer Ollama versions)
                {
                    "url": f"{self.base_url}/v1/chat/completions",
                    "payload": {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    "extract": lambda data: data.get("choices", [{}])[0].get("message", {}).get("content", "")
                },
                # OpenAI-compatible completions endpoint (fallback)
                {
                    "url": f"{self.base_url}/v1/completions",
                    "payload": {
                        "model": model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    "extract": lambda data: data.get("choices", [{}])[0].get("text", "")
                }
            ]
        
        errors = []
        for config in api_configs:
            try:
                logger.info(f"Trying Ollama endpoint: {config['url']}")
                response = requests.post(
                    config["url"], 
                    json=config["payload"], 
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()
                result = config["extract"](data)
                logger.info(f"Successfully generated text using {config['url']}")
                return result
            except Exception as e:
                error_msg = f"Error with {config['url']}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
        
        # If we've tried all endpoints and none worked, return a consolidated error
        error_msg = f"Error generating response with OLLAMA - all endpoints failed: {'; '.join(errors)}"
        logger.error(f"Error generating text with OLLAMA - all endpoints failed")
        return error_msg
    
    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Get embedding vector for text using OLLAMA
        
        Args:
            text: The text to get embedding for
            model: Model to use (defaults to configured model)
            
        Returns:
            List of float values representing the embedding or fallback embedding
        """
        model = model or self.model
        # Import config here to avoid potential scope issues
        import config as config_module
        ollama_version = config_module.OLLAMA_VERSION
        logger.info(f"Getting embeddings with Ollama version: {ollama_version}")
        
        try:
            # For Ollama 0.6.x
            if ollama_version.startswith("0.6"):
                # In 0.6.4, embeddings are accessed via /api/embeddings with 'prompt' field
                url = f"{self.base_url}/api/embeddings"
                logger.info(f"Using Ollama 0.6.x embeddings endpoint: {url}")
                
                # The 'prompt' field is used in 0.6.x
                payload = {
                    "model": model,
                    "prompt": text
                }
                
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    if "embedding" in data:
                        logger.info(f"Successfully retrieved embedding from {url} (embedding field)")
                        return data["embedding"]
                    else:
                        logger.warning(f"Unexpected response format from {url}: missing 'embedding' field")
                        return [0.0] * 384  # Return zero vector as fallback
                except Exception as e:
                    logger.error(f"Error with Ollama 0.6.x embeddings: {str(e)}")
                    return [0.0] * 384  # Return zero vector as fallback
            
            # For other Ollama versions - try various formats
            # Try standard Ollama embeddings API first
            url = f"{self.base_url}/api/embeddings"
            payload = {
                "model": model,
                "prompt": text
            }
            
            try:
                logger.info(f"Trying embeddings endpoint with 'prompt' field: {url}")
                response = requests.post(url, json=payload, timeout=10)
                response.raise_for_status()
                data = response.json()
                if "embedding" in data:
                    logger.info(f"Successfully retrieved embedding from {url} (embedding field)")
                    return data["embedding"]
                else:
                    logger.warning(f"Unexpected response format from {url}: missing 'embedding' field")
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # If 404, try with alternative format (input field)
                    logger.info(f"Trying newer Ollama embeddings API format with 'input' field (404 on {url})")
                    embeddings_url = f"{self.base_url}/api/embeddings"
                    payload = {
                        "model": model,
                        "input": text
                    }
                    response = requests.post(embeddings_url, json=payload, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    # Try different response formats
                    if "embedding" in data:
                        logger.info(f"Successfully retrieved embedding from {embeddings_url} (embedding field)")
                        return data["embedding"]
                    elif "data" in data and len(data["data"]) > 0:
                        logger.info(f"Successfully retrieved embedding from {embeddings_url} (data field)")
                        return data["data"][0].get("embedding", [])
                    else:
                        logger.warning(f"Unexpected response format from {embeddings_url}")
                        raise ValueError("Unexpected response format from embeddings API")
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Error getting embedding from OLLAMA: {str(e)}")
            # Return zero vector with standard dimensions as a fallback
            return [0.0] * 384
    
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
        # Import config here to avoid potential scope issues
        import config as config_module
        ollama_version = config_module.OLLAMA_VERSION
        logger.info(f"Using chat with Ollama version: {ollama_version}")
        
        # Format messages into a single prompt for models that don't support chat format natively
        prompt = self._format_chat_messages(messages)
        
        # For Ollama 0.6.x, try specific endpoints in order
        if ollama_version.startswith("0.6"):
            api_configs = [
                # Chat API for 0.6.x - primary endpoint for chat
                {
                    "url": f"{self.base_url}/api/chat",
                    "payload": {
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    "extract": lambda data: data.get("message", {}).get("content", "")
                },
                # Fallback to generate API for 0.6.x
                {
                    "url": f"{self.base_url}/api/generate",
                    "payload": {
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    },
                    "extract": lambda data: data.get("response", "")
                }
            ]
            
            errors = []
            for config in api_configs:
                try:
                    logger.info(f"Trying Ollama chat endpoint: {config['url']}")
                    response = requests.post(
                        config["url"], 
                        json=config["payload"], 
                        timeout=30
                    )
                    response.raise_for_status()
                    data = response.json()
                    result = config["extract"](data)
                    logger.info(f"Successfully generated chat response using {config['url']}")
                    return result
                except Exception as e:
                    error_msg = f"Error with {config['url']}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            # If we've tried all endpoints and none worked, return a consolidated error
            error_msg = f"Error generating chat response with OLLAMA - all endpoints failed: {'; '.join(errors)}"
            logger.error(error_msg)
            return error_msg
        
        # For other versions, try the standard approach first, then fall back
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
            
            logger.info(f"Trying standard chat endpoint: {url}")
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get("message", {}).get("content", "")
            
        except Exception as e:
            # Fallback to generate API if chat API fails
            logger.warning(f"Error using chat API with OLLAMA, falling back to generate: {str(e)}")
            try:
                return self.generate(prompt, model, temperature, max_tokens)
            except Exception as inner_e:
                error_msg = f"Error generating chat response with OLLAMA: {str(inner_e)}"
                logger.error(f"Error generating chat response with OLLAMA (fallback): {str(inner_e)}")
                return error_msg
    
    def _format_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Format chat messages into a single prompt string
        
        Args:
            messages: List of message objects with 'role' and 'content' keys
            
        Returns:
            Formatted prompt string
        """
        formatted = []
        
        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "")
            
            if role == "system":
                formatted.append(f"System: {content}")
            elif role == "user":
                formatted.append(f"User: {content}")
            elif role == "assistant":
                formatted.append(f"Assistant: {content}")
            else:
                formatted.append(f"{role.capitalize()}: {content}")
        
        formatted.append("Assistant: ")
        return "\n\n".join(formatted)


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
        logger.info("Legal Assistant initialized")
    
    def analyze_case(self, case_text: str) -> Dict[str, Any]:
        """
        Analyze a legal case to extract key information
        
        Args:
            case_text: Full text of the case
            
        Returns:
            Dictionary with analysis results
        """
        prompt = f"""
        Analyze the following legal case from the Kenyan legal system and extract the key information.
        
        {case_text}
        
        Format your response as a structured analysis with the following sections:
        1. Citation
        2. Court
        3. Judges
        4. Parties Involved
        5. Key Legal Issues
        6. Main Legal Principles Established
        7. Holding/Decision
        8. Reasoning
        9. Precedents Cited
        10. Statutes/Regulations Referenced
        """
        
        analysis_text = self.llm_client.generate(prompt)
        
        # Convert to structured format
        analysis = {
            "citation": self._extract_section(analysis_text, "Citation", "Court"),
            "court": self._extract_section(analysis_text, "Court", "Judges"),
            "judges": self._extract_section(analysis_text, "Judges", "Parties Involved"),
            "parties": self._extract_section(analysis_text, "Parties Involved", "Key Legal Issues"),
            "legal_issues": self._extract_section(analysis_text, "Key Legal Issues", "Main Legal Principles"),
            "legal_principles": self._extract_section(analysis_text, "Main Legal Principles", "Holding/Decision"),
            "decision": self._extract_section(analysis_text, "Holding/Decision", "Reasoning"),
            "reasoning": self._extract_section(analysis_text, "Reasoning", "Precedents Cited"),
            "precedents": self._extract_section(analysis_text, "Precedents Cited", "Statutes/Regulations"),
            "statutes": self._extract_section(analysis_text, "Statutes/Regulations", ""),
            "full_analysis": analysis_text
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
        # Format case_info as string
        case_info_str = "\n".join([f"{key}: {value}" for key, value in case_info.items()])
        
        prompt = f"""
        Draft a {document_type} for the Kenyan legal system based on the following case information and instructions.
        
        CASE INFORMATION:
        {case_info_str}
        
        SPECIFIC INSTRUCTIONS:
        {instructions}
        
        Please format the document appropriately for the Kenyan legal system.
        """
        
        return self.llm_client.generate(prompt)
    
    def analyze_statute(self, statute_text: str) -> Dict[str, Any]:
        """
        Analyze a statute to extract key information
        
        Args:
            statute_text: Full text of the statute
            
        Returns:
            Dictionary with analysis results
        """
        prompt = f"""
        Analyze the following statute from the Kenyan legal system and extract the key information.
        
        {statute_text}
        
        Format your response as a structured analysis with the following sections:
        1. Full Title of the Statute
        2. Date of Enactment
        3. Purpose and Scope
        4. Key Definitions
        5. Main Provisions
        6. Obligations Created
        7. Penalties or Consequences
        8. Related Regulations or Statutory Instruments
        """
        
        analysis_text = self.llm_client.generate(prompt)
        
        # Convert to structured format
        analysis = {
            "title": self._extract_section(analysis_text, "Full Title", "Date of Enactment"),
            "enactment_date": self._extract_section(analysis_text, "Date of Enactment", "Purpose and Scope"),
            "purpose": self._extract_section(analysis_text, "Purpose and Scope", "Key Definitions"),
            "definitions": self._extract_section(analysis_text, "Key Definitions", "Main Provisions"),
            "provisions": self._extract_section(analysis_text, "Main Provisions", "Obligations Created"),
            "obligations": self._extract_section(analysis_text, "Obligations Created", "Penalties or Consequences"),
            "penalties": self._extract_section(analysis_text, "Penalties or Consequences", "Related Regulations"),
            "related_regulations": self._extract_section(analysis_text, "Related Regulations", ""),
            "full_analysis": analysis_text
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
        # Format cases and statutes as string
        cases_str = "\n\n".join([
            f"Case: {case.get('citation', 'Unknown')}\n" +
            f"Holding: {case.get('decision', 'Unknown')}\n" +
            f"Reasoning: {case.get('reasoning', 'Unknown')}"
            for case in relevant_cases
        ])
        
        statutes_str = "\n\n".join([
            f"Statute: {statute.get('title', 'Unknown')}\n" +
            f"Purpose: {statute.get('purpose', 'Unknown')}\n" +
            f"Key Provisions: {statute.get('provisions', 'Unknown')}"
            for statute in relevant_statutes
        ])
        
        prompt = f"""
        Generate a legal research memorandum on the following topic for the Kenyan legal system.
        
        TOPIC:
        {topic}
        
        RELEVANT CASES:
        {cases_str}
        
        RELEVANT STATUTES:
        {statutes_str}
        
        Format your response as a formal legal research memorandum with the following sections:
        1. Introduction and Statement of the Legal Issue
        2. Brief Statement of the Conclusion
        3. Statement of Facts
        4. Discussion of Applicable Law
        5. Conclusion and Recommendations
        """
        
        return self.llm_client.generate(prompt)
    
    def generate_case_summary(self, case_text: str) -> str:
        """
        Generate a concise summary of a legal case
        
        Args:
            case_text: Full text of the case
            
        Returns:
            Concise case summary
        """
        prompt = f"""
        Please summarize the following Kenyan legal case in a concise and structured format.
        
        {case_text}
        
        Format your response as a structured summary with the following sections:
        1. Citation
        2. Parties Involved
        3. Court
        4. Key Facts
        5. Legal Issues Presented
        6. Court's Holding
        7. Key Reasoning
        8. Significance of the Decision
        """
        
        return self.llm_client.generate(prompt)
    
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
        Generate a contract clause for a {contract_type} under Kenyan law.
        
        PURPOSE OF THE CLAUSE:
        {clause_purpose}
        
        SPECIFIC REQUIREMENTS:
        {specific_requirements}
        
        Please draft a comprehensive, legally sound clause that would be suitable for inclusion in a formal contract under Kenyan law.
        """
        
        return self.llm_client.generate(prompt)
    
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
        try:
            # Special handling for test cases with the format "Key: Value"
            if section_start.endswith(':'):
                lines = text.strip().split('\n')
                for i, line in enumerate(lines):
                    if section_start in line:
                        # Extract the value after the colon
                        if ': ' in line:
                            content = line.split(': ', 1)[1].strip()
                            return content
                        
            # Find the start of the section
            start_index = text.find(section_start)
            if start_index == -1:
                # Try with a number prefix (e.g., "1. Citation")
                for i in range(1, 11):
                    start_index = text.find(f"{i}. {section_start}")
                    if start_index != -1:
                        start_index = text.find(section_start, start_index)
                        break
            
            if start_index == -1:
                return ""
            
            # Move to the end of the section title
            start_index = text.find("\n", start_index)
            if start_index == -1:
                return ""
            
            start_index += 1  # Skip the newline
            
            # Find the end of the section
            end_index = text.find(section_end, start_index)
            if section_end == "":
                end_index = len(text)
            elif end_index == -1:
                # Try with a number prefix
                for i in range(1, 11):
                    end_index = text.find(f"{i}. {section_end}", start_index)
                    if end_index != -1:
                        break
                if end_index == -1:
                    end_index = len(text)
            
            # Extract and clean the section
            section_text = text[start_index:end_index].strip()
            return section_text
            
        except Exception as e:
            logger.error(f"Error extracting section {section_start}: {str(e)}")
            return ""