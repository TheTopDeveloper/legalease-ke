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
            
            # Generate arguments based on precedents
            arguments_prompt = f"""
            Based on the Kenyan legal precedents above related to: {issue}
            
            Please provide 3-5 strong legal arguments that can be made based on these precedents. For each argument:
            1. State the argument clearly and concisely
            2. Identify the supporting precedent(s)
            3. Explain why the precedent supports this argument
            4. Note any potential weaknesses in the argument
            
            Focus on arguments that would be persuasive in a Kenyan court.
            """
            
            arguments_response = self.llm_client.generate(arguments_prompt, temperature=0.3, max_tokens=1000)
            results['arguments'] = arguments_response
            
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
            
    def generate_legal_arguments(self, issue: str, case_facts: str, opposing_arguments: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate legal arguments, supporting evidence, and rebuttals
        
        Args:
            issue: Legal issue to argue
            case_facts: Facts of the case
            opposing_arguments: Optional opposing arguments to rebut
            
        Returns:
            Arguments, evidence, and rebuttals
        """
        logger.info(f"Generating legal arguments for issue: {issue}")
        
        try:
            # Search for relevant cases and statutes first
            search_results = self.scraper.search_cases(issue)
            
            # Get details for top cases
            cases = []
            for result in search_results[:5]:  # Limit to 5 cases
                case_url = result.get('link')
                if case_url:
                    case_details = self.scraper.get_case_details(case_url)
                    if case_details:
                        cases.append(case_details)
            
            # Get relevant legislation
            statutes = self.scraper.get_legislation()[:5]  # Limit to 5 statutes
            
            # Generate arguments based on gathered evidence
            arguments_prompt = f"""
            Please analyze this Kenyan legal issue and provide strong legal arguments:
            
            ISSUE: {issue}
            
            CASE FACTS:
            {case_facts}
            
            RELEVANT CASES:
            {json.dumps([{
                'title': case.get('title', ''),
                'citation': case.get('citation', ''),
                'court': case.get('court', ''),
                'summary': case.get('summary', '')
            } for case in cases], indent=2)}
            
            RELEVANT STATUTES:
            {json.dumps([{
                'title': statute.get('title', '')
            } for statute in statutes], indent=2)}
            
            Please provide:
            1. 3-5 strong arguments supporting the position on this issue
            2. For each argument, provide:
               a. The clear legal argument
               b. Supporting evidence from cases and statutes
               c. How the law applies to the case facts
               d. Anticipated counter-arguments
            
            Format each argument clearly with headings and structured evidence.
            """
            
            arguments_response = self.llm_client.generate(arguments_prompt, temperature=0.3, max_tokens=1500)
            
            # Generate evidence matrix
            evidence_prompt = f"""
            Based on the Kenyan legal issue and case facts:
            
            ISSUE: {issue}
            
            CASE FACTS:
            {case_facts}
            
            Please create an evidence matrix listing:
            1. Each key fact or piece of evidence
            2. The legal significance of the evidence
            3. Related legal authorities (cases or statutes)
            4. Strength of evidence (strong, moderate, weak)
            5. How to effectively present this evidence
            
            Focus on the most compelling evidence that would be persuasive in a Kenyan court.
            """
            
            evidence_response = self.llm_client.generate(evidence_prompt, temperature=0.2, max_tokens=1000)
            
            results = {
                'issue': issue,
                'arguments': arguments_response,
                'evidence': evidence_response,
                'related_cases': [{
                    'title': case.get('title', ''),
                    'citation': case.get('citation', ''),
                    'court': case.get('court', ''),
                    'link': case.get('link', '')
                } for case in cases],
                'related_statutes': [{
                    'title': statute.get('title', ''),
                    'link': statute.get('link', '')
                } for statute in statutes]
            }
            
            # Generate rebuttals if opposing arguments are provided
            if opposing_arguments:
                rebuttal_prompt = f"""
                Please analyze these opposing arguments in a Kenyan legal context and provide effective rebuttals:
                
                ISSUE: {issue}
                
                CASE FACTS:
                {case_facts}
                
                OPPOSING ARGUMENTS:
                {opposing_arguments}
                
                RELEVANT CASES AND STATUTES:
                {json.dumps([{
                    'title': case.get('title', ''),
                    'citation': case.get('citation', ''),
                } for case in cases], indent=2)}
                
                Please provide:
                1. Point-by-point rebuttals to each opposing argument
                2. Legal authorities that counter the opposing arguments
                3. Alternative interpretations of facts or law that weaken opposing positions
                4. Strategic recommendations for addressing these arguments in court
                
                Focus on rebuttals that would be persuasive in a Kenyan court based on Kenyan law.
                """
                
                rebuttal_response = self.llm_client.generate(rebuttal_prompt, temperature=0.3, max_tokens=1500)
                results['rebuttals'] = rebuttal_response
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating legal arguments: {str(e)}")
            return {
                'issue': issue,
                'error': str(e),
                'arguments': [],
                'evidence': [],
                'rebuttals': []
            }
