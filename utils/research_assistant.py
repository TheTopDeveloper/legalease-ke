import logging
import json
from typing import List, Dict, Any, Optional
from utils.scraper import KenyaLawScraper
from utils.llm import OllamaClient, LegalAssistant
from utils.vector_db import VectorDatabase

logger = logging.getLogger(__name__)

class LegalResearchAssistant:
    """
    Legal research assistant for Kenyan law
    """
    
    def __init__(self, scraper=None, llm_client=None, vector_db=None):
        """
        Initialize legal research assistant
        
        Args:
            scraper: Kenya Law scraper
            llm_client: LLM client for analysis
            vector_db: Vector database for semantic search
        """
        self.scraper = scraper or KenyaLawScraper()
        self.llm_client = llm_client or OllamaClient()
        self.legal_assistant = LegalAssistant(self.llm_client)
        self.vector_db = vector_db or VectorDatabase()
        
        logger.info("Initialized legal research assistant")
    
    def research_legal_issue(self, query: str, court_filters: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Research a legal issue
        
        Args:
            query: Research query
            court_filters: List of court codes to filter by
            
        Returns:
            Research results
        """
        logger.info(f"Researching legal issue: {query}")
        results = {
            'query': query,
            'summary': '',
            'cases': [],
            'statutes': [],
            'principles': [],
            'recommendations': ''
        }
        
        try:
            # Search for cases using web scraper
            search_results = self.scraper.search_cases(query)
            
            # Filter by courts if specified
            if court_filters:
                search_results = [
                    result for result in search_results 
                    if any(court_code in result.get('link', '') for court_code in court_filters)
                ]
            
            # Get case details for top results
            cases = []
            for result in search_results[:3]:  # Limit to 3 cases for detail retrieval
                case_url = result.get('link')
                if case_url:
                    case_details = self.scraper.get_case_details(case_url)
                    if case_details:
                        # Get AI analysis of the case
                        case_analysis = self.legal_assistant.analyze_case(case_details.get('full_text', ''))
                        
                        # Add analysis to case details
                        case_details['analysis'] = case_analysis
                        cases.append(case_details)
            
            results['cases'] = cases
            
            # Search for relevant statutes
            statutes = self.scraper.get_legislation()
            results['statutes'] = statutes[:3]  # Limit to 3 statutes
            
            # Also search vector database for related documents
            vector_results = self.vector_db.search_all(query, n_results=3)
            
            # Add vector database results
            if vector_results.get('cases'):
                results['vector_cases'] = vector_results['cases']
            
            if vector_results.get('statutes'):
                results['vector_statutes'] = vector_results['statutes']
            
            # Generate research summary and recommendations
            summary_prompt = f"""
            Please analyze these research results on Kenyan law regarding: {query}
            
            CASES FOUND:
            {json.dumps([{
                'title': case.get('title', ''),
                'citation': case.get('citation', ''),
                'court': case.get('court', ''),
                'summary': case.get('analysis', {}).get('summary', '') if case.get('analysis') else ''
            } for case in cases], indent=2)}
            
            STATUTES FOUND:
            {json.dumps([{
                'title': statute.get('title', '')
            } for statute in statutes[:3]], indent=2)}
            
            Please provide:
            1. A concise summary of the key legal principles related to this issue
            2. The most relevant legal authorities (cases and statutes)
            3. How these authorities apply to the query
            4. Recommendations for further research or legal strategy
            """
            
            summary_response = self.llm_client.generate(summary_prompt, temperature=0.3, max_tokens=1500)
            
            # Extract key legal principles
            principles_prompt = f"""
            Based on the Kenyan law cases and statutes relating to: {query}
            
            Please extract and list the 3-5 most important legal principles established by these cases and statutes.
            For each principle, provide:
            1. A clear statement of the principle
            2. The source (case or statute) establishing it
            3. How it's relevant to the query
            
            Format each principle clearly and concisely.
            """
            
            principles_response = self.llm_client.generate(principles_prompt, temperature=0.2, max_tokens=800)
            
            # Add generated content to results
            results['summary'] = summary_response
            results['principles'] = principles_response
            
            # Generate recommendations
            recommendations_prompt = f"""
            Based on the Kenyan law research regarding: {query}
            
            Please provide specific recommendations for:
            1. The strongest legal arguments to make
            2. Potential counter-arguments to prepare for
            3. Additional research areas that might strengthen the case
            4. Practical steps to take based on this legal research
            
            Be specific and cite relevant Kenyan legal authorities where possible.
            """
            
            recommendations_response = self.llm_client.generate(recommendations_prompt, temperature=0.3, max_tokens=800)
            results['recommendations'] = recommendations_response
            
            return results
        
        except Exception as e:
            logger.error(f"Error researching legal issue: {str(e)}")
            results['error'] = str(e)
            return results
    
    def analyze_legal_document(self, document_text: str) -> Dict[str, Any]:
        """
        Analyze a legal document
        
        Args:
            document_text: Text of the document
            
        Returns:
            Analysis results
        """
        logger.info("Analyzing legal document")
        
        try:
            # Determine document type
            type_prompt = f"""
            Please identify the type of Kenyan legal document from the following text:
            
            {document_text[:1000]}...
            
            Possible types include:
            - Court ruling/judgment
            - Pleading
            - Contract
            - Legal notice
            - Statute or regulation
            - Affidavit
            - Legal opinion
            - Demand letter
            
            Just respond with the document type.
            """
            
            document_type = self.llm_client.generate(type_prompt, temperature=0.1, max_tokens=50).strip()
            
            # Analyze based on document type
            if "judgment" in document_type.lower() or "ruling" in document_type.lower():
                analysis = self.legal_assistant.analyze_case(document_text)
            elif "statute" in document_type.lower() or "regulation" in document_type.lower():
                analysis = self.legal_assistant.analyze_statute(document_text)
            else:
                # General document analysis
                analysis_prompt = f"""
                Please analyze this Kenyan legal document ({document_type}) and provide:
                
                1. A summary of the document's purpose
                2. Key parties mentioned
                3. Important dates and deadlines
                4. Legal obligations or rights established
                5. Potential issues or concerns with the document
                6. Recommendations for the user
                
                Document text:
                {document_text[:5000]}... [truncated]
                """
                
                analysis_response = self.llm_client.generate(analysis_prompt, temperature=0.2, max_tokens=1200)
                
                analysis = {
                    'document_type': document_type,
                    'analysis': analysis_response
                }
            
            return {
                'document_type': document_type,
                'analysis': analysis
            }
        
        except Exception as e:
            logger.error(f"Error analyzing legal document: {str(e)}")
            return {
                'error': str(e)
            }
    
    def find_relevant_precedents(self, issue: str, court_level: str) -> Dict[str, Any]:
        """
        Find relevant precedents for a legal issue
        
        Args:
            issue: Legal issue
            court_level: Court level (e.g., 'Supreme Court', 'Court of Appeal')
            
        Returns:
            Relevant precedents
        """
        logger.info(f"Finding relevant precedents for issue: {issue}, court level: {court_level}")
        
        court_hierarchy = {
            'Supreme Court': ['KESC'],
            'Court of Appeal': ['KESC', 'KECA'],
            'High Court': ['KESC', 'KECA', 'KEHC'],
            'Employment and Labour Relations Court': ['KESC', 'KECA', 'KEELRC'],
            'Environment and Land Court': ['KESC', 'KECA', 'KEELC'],
            'Magistrate\'s Court': ['KESC', 'KECA', 'KEHC', 'KEMC']
        }
        
        courts_to_search = court_hierarchy.get(court_level, ['KESC', 'KECA', 'KEHC'])
        
        try:
            results = {
                'issue': issue,
                'court_level': court_level,
                'binding_precedents': [],
                'persuasive_precedents': []
            }
            
            # Search for precedents using web scraper
            for court_code in courts_to_search:
                # Get cases for this court
                cases = self.scraper.get_case_law(court_code)
                
                # Search these cases for relevance to the issue
                search_results = self.scraper.search_cases(issue)
                
                # Filter to this court's cases
                court_search_results = [
                    result for result in search_results 
                    if court_code in result.get('link', '')
                ]
                
                # Get case details for top results
                for result in court_search_results[:2]:  # Limit to 2 cases per court
                    case_url = result.get('link')
                    if case_url:
                        case_details = self.scraper.get_case_details(case_url)
                        if case_details:
                            # Get AI analysis of the case
                            case_analysis = self.legal_assistant.analyze_case(case_details.get('full_text', ''))
                            
                            # Add analysis to case details
                            case_details['analysis'] = case_analysis
                            
                            # Determine if this is binding or persuasive precedent
                            if court_code in courts_to_search[:courts_to_search.index(courts_to_search[0]) + 1]:
                                results['binding_precedents'].append(case_details)
                            else:
                                results['persuasive_precedents'].append(case_details)
            
            # Also search vector database for related cases
            vector_results = self.vector_db.search_cases(issue, n_results=5)
            results['vector_results'] = vector_results
            
            # Generate analysis of found precedents
            precedents_analysis_prompt = f"""
            Please analyze these Kenyan legal precedents related to: {issue}
            
            BINDING PRECEDENTS:
            {json.dumps([{
                'title': case.get('title', ''),
                'citation': case.get('citation', ''),
                'court': case.get('court', ''),
                'summary': case.get('analysis', {}).get('summary', '') if case.get('analysis') else ''
            } for case in results['binding_precedents']], indent=2)}
            
            PERSUASIVE PRECEDENTS:
            {json.dumps([{
                'title': case.get('title', ''),
                'citation': case.get('citation', ''),
                'court': case.get('court', ''),
                'summary': case.get('analysis', {}).get('summary', '') if case.get('analysis') else ''
            } for case in results['persuasive_precedents']], indent=2)}
            
            Please provide:
            1. An analysis of how these precedents apply to the legal issue
            2. The key legal principles established by these precedents
            3. How the precedents might be effectively used in legal argumentation
            4. Any conflicting precedents and how to address them
            """
            
            analysis_response = self.llm_client.generate(precedents_analysis_prompt, temperature=0.3, max_tokens=1500)
            results['analysis'] = analysis_response
            
            return results
        
        except Exception as e:
            logger.error(f"Error finding relevant precedents: {str(e)}")
            return {
                'issue': issue,
                'court_level': court_level,
                'error': str(e),
                'binding_precedents': [],
                'persuasive_precedents': []
            }
