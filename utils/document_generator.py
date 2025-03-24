import os
import logging
import jinja2
import datetime
from typing import Dict, Any
import re
from utils.llm import OllamaClient, LegalAssistant
import config

logger = logging.getLogger(__name__)

class DocumentGenerator:
    """
    Document generator for creating legal documents from templates
    """
    
    def __init__(self, templates_dir=None, llm_client=None):
        """
        Initialize document generator
        
        Args:
            templates_dir: Directory containing templates
            llm_client: LLM client for document generation
        """
        self.templates_dir = templates_dir or config.TEMPLATES_DIR
        self.llm_client = llm_client or OllamaClient()
        self.legal_assistant = LegalAssistant(llm_client)
        
        # Create templates directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Initialize Jinja environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.templates_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Create default templates if they don't exist
        self._create_default_templates()
        
        logger.info(f"Initialized document generator with templates directory: {self.templates_dir}")
    
    def _create_default_templates(self):
        """Create default templates if they don't exist"""
        default_templates = {
            "pleading_template.txt": self._get_pleading_template(),
            "contract_template.txt": self._get_contract_template(),
            "legal_opinion_template.txt": self._get_legal_opinion_template(),
            "affidavit_template.txt": self._get_affidavit_template(),
            "demand_letter_template.txt": self._get_demand_letter_template()
        }
        
        for filename, content in default_templates.items():
            file_path = os.path.join(self.templates_dir, filename)
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    f.write(content)
                logger.info(f"Created default template: {filename}")
    
    def _get_pleading_template(self):
        """Get default pleading template"""
        return """
REPUBLIC OF KENYA
IN THE {{ court_name }} AT {{ court_location }}

{{ case_type }} CASE NO. {{ case_number }} OF {{ year }}

BETWEEN

{{ plaintiff }} ............................................................. PLAINTIFF

AND

{{ defendant }} ........................................................... DEFENDANT

{{ document_title|upper }}

{{ document_content }}

DATED at {{ city }} this {{ day }} day of {{ month }} {{ year }}

DRAWN & FILED BY:
{{ law_firm }}
Advocates for the {{ party }}
{{ address }}
{{ contact_info }}
"""
    
    def _get_contract_template(self):
        """Get default contract template"""
        return """
{{ contract_title|upper }}

THIS AGREEMENT is made on the {{ day }} day of {{ month }} {{ year }}

BETWEEN:

{{ party1_name }} of {{ party1_address }} (hereinafter referred to as "{{ party1_reference }}")

AND

{{ party2_name }} of {{ party2_address }} (hereinafter referred to as "{{ party2_reference }}")

WHEREAS:

{{ recitals }}

NOW THEREFORE IT IS HEREBY AGREED as follows:

{{ contract_clauses }}

IN WITNESS WHEREOF the parties hereto have executed this Agreement on the day and year first above written.

SIGNED by {{ party1_name }}        )
                                  )
                                  ) ___________________________
in the presence of:               )
                                  
Witness: ______________________
Name: _________________________
Address: ______________________
Occupation: ___________________

SIGNED by {{ party2_name }}        )
                                  )
                                  ) ___________________________
in the presence of:               )
                                  
Witness: ______________________
Name: _________________________
Address: ______________________
Occupation: ___________________
"""
    
    def _get_legal_opinion_template(self):
        """Get default legal opinion template"""
        return """
{{ law_firm_letterhead }}

{{ date }}

{{ client_name }}
{{ client_address }}

Dear {{ client_salutation }},

RE: LEGAL OPINION - {{ opinion_subject }}

We refer to your letter dated {{ reference_date }} wherein you sought our opinion on {{ opinion_subject }}.

1. BACKGROUND

{{ background }}

2. ISSUES FOR CONSIDERATION

{{ issues }}

3. APPLICABLE LAW

{{ applicable_law }}

4. ANALYSIS

{{ analysis }}

5. OPINION

{{ opinion }}

Please note that this opinion is based on the information provided to us and the laws of Kenya as at the date of this opinion. Should you require any clarification or have any further queries, please do not hesitate to contact the undersigned.

Yours faithfully,

{{ lawyer_name }}
{{ lawyer_title }}
{{ law_firm }}
"""
    
    def _get_affidavit_template(self):
        """Get default affidavit template"""
        return """
REPUBLIC OF KENYA
IN THE {{ court_name }} AT {{ court_location }}

{{ case_type }} CASE NO. {{ case_number }} OF {{ year }}

BETWEEN

{{ plaintiff }} ............................................................. PLAINTIFF

AND

{{ defendant }} ........................................................... DEFENDANT

AFFIDAVIT

I, {{ deponent_name }} of Post Office Box Number {{ deponent_address }} and residing at {{ deponent_residence }}, {{ deponent_occupation }}, do make oath and state as follows:

{{ affidavit_content }}

SWORN at {{ city }}            )
this {{ day }} day of {{ month }} {{ year }}  ) ________________________
by the said {{ deponent_name }}    )          DEPONENT
                                  )
BEFORE ME                        )
                                  )
                                  )
COMMISSIONER FOR OATHS            )
"""
    
    def _get_demand_letter_template(self):
        """Get default demand letter template"""
        return """
{{ law_firm_letterhead }}

{{ date }}

{{ recipient_name }}
{{ recipient_address }}

Dear Sir/Madam,

RE: {{ demand_subject }}

We act for {{ client_name }} (our client), and have been instructed to address you as follows:

{{ demand_content }}

TAKE NOTICE that unless we receive your payment/response within {{ response_period }} days from the date of this letter, we have firm instructions to institute legal proceedings against you without further reference to you and at your own risk as to costs and incidental expenses.

Yours faithfully,

{{ lawyer_name }}
{{ lawyer_title }}
{{ law_firm }}
"""
    
    def generate_document_from_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Generate a document using a template file
        
        Args:
            template_name: Name of the template
            context: Dictionary with template variables
            
        Returns:
            Generated document
        """
        try:
            template = self.jinja_env.get_template(template_name)
            
            # Add date-related context if not provided
            now = datetime.datetime.now()
            if 'day' not in context:
                context['day'] = now.day
            if 'month' not in context:
                context['month'] = now.strftime("%B")
            if 'year' not in context:
                context['year'] = now.year
            if 'date' not in context:
                context['date'] = now.strftime("%d %B %Y")
            
            # Generate document
            document = template.render(**context)
            logger.info(f"Generated document from template: {template_name}")
            
            return document
        
        except Exception as e:
            logger.error(f"Error generating document from template {template_name}: {str(e)}")
            return f"Error generating document: {str(e)}"
            
    def generate_from_user_template(self, template_content: str, context: Dict[str, Any]) -> str:
        """
        Generate a document using a template string from the database
        
        Args:
            template_content: Content of the template as a string
            context: Dictionary with template variables
            
        Returns:
            Generated document
        """
        try:
            # Create a template from the string
            template = jinja2.Template(template_content)
            
            # Add date-related context if not provided
            now = datetime.datetime.now()
            if 'day' not in context:
                context['day'] = now.day
            if 'month' not in context:
                context['month'] = now.strftime("%B")
            if 'year' not in context:
                context['year'] = now.year
            if 'date' not in context:
                context['date'] = now.strftime("%d %B %Y")
            
            # Generate document
            document = template.render(**context)
            logger.info("Generated document from user template")
            
            return document
        
        except Exception as e:
            logger.error(f"Error generating document from user template: {str(e)}")
            return f"Error generating document: {str(e)}"
    
    def generate_pleading(self, case_info: Dict[str, Any], document_info: Dict[str, Any]) -> str:
        """
        Generate a pleading document
        
        Args:
            case_info: Information about the case
            document_info: Information about the document
            
        Returns:
            Generated pleading document
        """
        context = {
            'court_name': case_info.get('court_level', ''),
            'court_location': case_info.get('court_location', ''),
            'case_type': case_info.get('case_type', ''),
            'case_number': case_info.get('case_number', ''),
            'plaintiff': case_info.get('plaintiff', ''),
            'defendant': case_info.get('defendant', ''),
            'document_title': document_info.get('title', ''),
            'document_content': document_info.get('content', ''),
            'city': document_info.get('city', 'Nairobi'),
            'party': document_info.get('party', 'Plaintiff'),
            'law_firm': document_info.get('law_firm', ''),
            'address': document_info.get('address', ''),
            'contact_info': document_info.get('contact_info', '')
        }
        
        return self.generate_document_from_template('pleading_template.txt', context)
    
    def generate_contract(self, contract_info: Dict[str, Any]) -> str:
        """
        Generate a contract document
        
        Args:
            contract_info: Information about the contract
            
        Returns:
            Generated contract document
        """
        context = {
            'contract_title': contract_info.get('title', ''),
            'party1_name': contract_info.get('party1_name', ''),
            'party1_address': contract_info.get('party1_address', ''),
            'party1_reference': contract_info.get('party1_reference', 'First Party'),
            'party2_name': contract_info.get('party2_name', ''),
            'party2_address': contract_info.get('party2_address', ''),
            'party2_reference': contract_info.get('party2_reference', 'Second Party'),
            'recitals': contract_info.get('recitals', ''),
            'contract_clauses': contract_info.get('contract_clauses', '')
        }
        
        return self.generate_document_from_template('contract_template.txt', context)
    
    def generate_legal_opinion(self, opinion_info: Dict[str, Any]) -> str:
        """
        Generate a legal opinion document
        
        Args:
            opinion_info: Information about the legal opinion
            
        Returns:
            Generated legal opinion document
        """
        context = {
            'law_firm_letterhead': opinion_info.get('law_firm_letterhead', ''),
            'client_name': opinion_info.get('client_name', ''),
            'client_address': opinion_info.get('client_address', ''),
            'client_salutation': opinion_info.get('client_salutation', 'Sir/Madam'),
            'opinion_subject': opinion_info.get('subject', ''),
            'reference_date': opinion_info.get('reference_date', ''),
            'background': opinion_info.get('background', ''),
            'issues': opinion_info.get('issues', ''),
            'applicable_law': opinion_info.get('applicable_law', ''),
            'analysis': opinion_info.get('analysis', ''),
            'opinion': opinion_info.get('opinion', ''),
            'lawyer_name': opinion_info.get('lawyer_name', ''),
            'lawyer_title': opinion_info.get('lawyer_title', ''),
            'law_firm': opinion_info.get('law_firm', '')
        }
        
        return self.generate_document_from_template('legal_opinion_template.txt', context)
    
    def generate_ai_document(self, document_type: str, instructions: str, context: Dict[str, Any]) -> str:
        """
        Generate a document using AI
        
        Args:
            document_type: Type of document to generate
            instructions: Instructions for document generation
            context: Additional context information
            
        Returns:
            AI-generated document
        """
        try:
            # Generate document using LLM
            document = self.legal_assistant.draft_legal_document(document_type, context, instructions)
            
            # If LLM returned None (connection failed), use template-based fallback
            if document is None:
                logger.warning(f"LLM connection failed, using template-based fallback for {document_type}")
                return self._generate_template_fallback(document_type, context)
            
            logger.info(f"Generated {document_type} document using AI")
            return document
        
        except Exception as e:
            logger.error(f"Error generating {document_type} document using AI: {str(e)}")
            return self._generate_template_fallback(document_type, context)
            
    def _generate_template_fallback(self, document_type: str, context: Dict[str, Any]) -> str:
        """
        Generate a document using templates when AI is not available
        
        Args:
            document_type: Type of document to generate
            context: Context information
            
        Returns:
            Template-based document
        """
        try:
            # Use appropriate template based on document type
            if document_type.lower() in ['pleading', 'plaint', 'application', 'petition']:
                template_name = "pleading_template.txt"
            elif document_type.lower() in ['contract', 'agreement']:
                template_name = "contract_template.txt"
            elif document_type.lower() in ['legal opinion', 'opinion', 'legal advice']:
                template_name = "legal_opinion_template.txt"
            elif document_type.lower() in ['affidavit', 'sworn statement']:
                template_name = "affidavit_template.txt"
            elif document_type.lower() in ['demand letter', 'letter of demand']:
                template_name = "demand_letter_template.txt"
            else:
                # Default to generic template
                template_name = "pleading_template.txt"
            
            # Add current date information if not provided
            now = datetime.datetime.now()
            if 'day' not in context:
                context['day'] = now.day
            if 'month' not in context:
                context['month'] = now.strftime('%B')
            if 'year' not in context:
                context['year'] = now.year
            
            # Add placeholder text for required fields if missing
            required_fields = ['court_name', 'court_location', 'case_number', 'plaintiff', 
                              'defendant', 'document_title', 'document_content', 'city',
                              'law_firm', 'party', 'address', 'contact_info']
                              
            for field in required_fields:
                if field not in context:
                    context[field] = f"[INSERT {field.upper()}]"
            
            # Generate document from template
            document = self.generate_document_from_template(template_name, context)
            logger.info(f"Generated {document_type} document using template fallback")
            
            return document
        
        except Exception as e:
            logger.error(f"Error in template fallback for {document_type}: {str(e)}")
            return f"""
DOCUMENT GENERATION FALLBACK

Document Type: {document_type}

Unable to generate document due to AI service unavailability.
Please try again later or use the template editor to create this document manually.

Error details: {str(e)}
"""
    
    def extract_document_metadata(self, document: str) -> Dict[str, Any]:
        """
        Extract metadata from a document
        
        Args:
            document: Document text
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {
            'title': '',
            'parties': [],
            'court': '',
            'case_number': '',
            'date': '',
            'citations': []
        }
        
        # Extract title (usually at the beginning, often in uppercase)
        title_match = re.search(r'^(.*?)(?=\n\n|\Z)', document, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Extract case number
        case_number_match = re.search(r'CASE\s+NO\.?\s+(\w+/\d+|\d+)\s+OF\s+(\d{4})', document, re.IGNORECASE)
        if case_number_match:
            metadata['case_number'] = f"{case_number_match.group(1)} of {case_number_match.group(2)}"
        
        # Extract court
        court_match = re.search(r'IN\s+THE\s+(.*?)\s+(?:AT|OF)\s+(.*?)(?=\n)', document, re.IGNORECASE)
        if court_match:
            metadata['court'] = f"{court_match.group(1)} at {court_match.group(2)}".strip()
        
        # Extract parties
        plaintiff_match = re.search(r'(.*?)\s*\.+\s*(?:PLAINTIFF|PETITIONER|APPLICANT)', document, re.IGNORECASE)
        defendant_match = re.search(r'(.*?)\s*\.+\s*(?:DEFENDANT|RESPONDENT)', document, re.IGNORECASE)
        
        if plaintiff_match:
            metadata['parties'].append({
                'role': 'Plaintiff',
                'name': plaintiff_match.group(1).strip()
            })
        
        if defendant_match:
            metadata['parties'].append({
                'role': 'Defendant',
                'name': defendant_match.group(1).strip()
            })
        
        # Extract date
        date_match = re.search(r'DATED\s+(?:at|on)\s+.*?\s+this\s+(\d+)(?:st|nd|rd|th)?\s+day\s+of\s+(\w+)\s+(\d{4})', document, re.IGNORECASE)
        if date_match:
            day = date_match.group(1)
            month = date_match.group(2)
            year = date_match.group(3)
            metadata['date'] = f"{day} {month} {year}"
        
        # Extract citations
        citation_pattern = r'\[(\d{4})\]\s+(\w+)\s+(\d+)'
        citation_matches = re.finditer(citation_pattern, document)
        
        for match in citation_matches:
            metadata['citations'].append({
                'year': match.group(1),
                'court': match.group(2),
                'number': match.group(3),
                'full': match.group(0)
            })
        
        return metadata
