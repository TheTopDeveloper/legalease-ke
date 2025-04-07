import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
#Postgres Configuration
DATABASE_URL="postgresql://legaluser:Abc.123@localhost:5432/legalease"
# Database configuration
#DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///kenyalaw.db")

# Kenya Law API configuration
KENYALAW_BASE_URL = "https://new.kenyalaw.org"

# OLLAMA configuration
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_PRIMARY_MODEL = os.environ.get("OLLAMA_PRIMARY_MODEL", "llama3:latest")
OLLAMA_SECONDARY_MODEL = os.environ.get("OLLAMA_SECONDARY_MODEL", "deepseek:latest")

# Enable LLM counter-checking?
ENABLE_LLM_COUNTERCHECK = os.environ.get("ENABLE_LLM_COUNTERCHECK", "True").lower() in ("true", "1", "yes")

# Vector database configuration
VECTOR_DB_PATH = os.environ.get("VECTOR_DB_PATH", "./vector_db")

# Session configuration
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Document templates directory
TEMPLATES_DIR = os.environ.get("TEMPLATES_DIR", "./document_templates")

# Configure court levels for the Kenyan judicial system
COURT_LEVELS = {
    "Supreme Court": "KESC",
    "Court of Appeal": "KECA",
    "High Court": "KEHC",
    "Employment and Labour Relations Court": "KEELRC",
    "Environment and Land Court": "KEELC",
    "Industrial Court": "KEIC",
    "Magistrate's Court": "KEMC",
    "Kadhis Courts": "KEKC",
    "Small Claims Court": "SCC"
}

# Configure case types
CASE_TYPES = [
    "Civil",
    "Criminal",
    "Commercial",
    "Constitutional",
    "Family",
    "Land",
    "Employment",
    "Tax",
    "Administrative",
    "Judicial Review"
]

# Configure practice areas
PRACTICE_AREAS = [
    "Corporate and Commercial",
    "Dispute Resolution",
    "Real Estate and Construction",
    "Banking and Finance",
    "Intellectual Property",
    "Employment and Labor",
    "Tax",
    "Constitutional and Human Rights",
    "Family Law",
    "Criminal Law"
]

# Document types
DOCUMENT_TYPES = [
    "Pleadings",
    "Affidavits",
    "Legal Notices",
    "Contracts",
    "Agreements",
    "Court Orders",
    "Rulings",
    "Judgments",
    "Legal Opinions",
    "Demand Letters"
]

# Contract types
CONTRACT_TYPES = [
    "Sale Agreement",
    "Lease Agreement",
    "Employment Contract",
    "Service Agreement",
    "Non-Disclosure Agreement",
    "Joint Venture Agreement",
    "Distribution Agreement",
    "Loan Agreement",
    "Consulting Agreement",
    "Franchise Agreement"
]
