import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import uuid
from utils.llm import OllamaClient
import config

logger = logging.getLogger(__name__)

class VectorDatabase:
    """
    Vector database for semantic search of legal documents
    """
    
    def __init__(self, db_path=None, llm_client=None):
        """
        Initialize vector database
        
        Args:
            db_path: Path to vector database
            llm_client: LLM client for embeddings (defaults to OllamaClient)
        """
        self.db_path = db_path or config.VECTOR_DB_PATH
        self.llm_client = llm_client or OllamaClient()
        
        # Ensure directory exists
        os.makedirs(self.db_path, exist_ok=True)
        
        # Initialize ChromaDB client
        self.chroma_client = chromadb.PersistentClient(path=self.db_path)
        
        # Create collections if they don't exist
        self._create_collections()
        
        logger.info(f"Initialized vector database at {self.db_path}")
    
    def _create_collections(self):
        """Create collections for different document types"""
        try:
            # Define custom embedding function using our LLM client
            class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
                def __init__(self, llm_client):
                    self.llm_client = llm_client
                
                def __call__(self, texts):
                    # Get embeddings for each text
                    embeddings = [self.llm_client.get_embedding(text) for text in texts]
                    
                    # Convert numpy arrays to lists if needed
                    processed_embeddings = []
                    for emb in embeddings:
                        if isinstance(emb, np.ndarray):
                            processed_embeddings.append(emb.tolist())
                        else:
                            processed_embeddings.append(emb)
                    
                    return processed_embeddings
                
            self.embedding_function = CustomEmbeddingFunction(self.llm_client)
            
            # Create collections for different document types
            self.case_collection = self._get_or_create_collection("cases")
            self.statute_collection = self._get_or_create_collection("statutes")
            self.document_collection = self._get_or_create_collection("documents")
            self.contract_collection = self._get_or_create_collection("contracts")
            
            logger.info("Vector database collections created/loaded")
        
        except Exception as e:
            logger.error(f"Error creating vector database collections: {str(e)}")
    
    def _get_or_create_collection(self, name):
        """Get or create a collection with the given name"""
        try:
            return self.chroma_client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_function
            )
        except Exception as e:
            logger.error(f"Error creating collection {name}: {str(e)}")
            # Fallback to creating without embedding function
            return self.chroma_client.get_or_create_collection(name=name)
    
    def add_case(self, case_data: Dict[str, Any]) -> str:
        """
        Add a case to the vector database
        
        Args:
            case_data: Dictionary with case information
            
        Returns:
            ID of the added case
        """
        try:
            # Generate an ID if none provided
            doc_id = case_data.get('id', str(uuid.uuid4()))
            
            # Prepare text for embedding
            text_for_embedding = f"""
            Title: {case_data.get('title', '')}
            Citation: {case_data.get('citation', '')}
            Court: {case_data.get('court', '')}
            Parties: {case_data.get('parties', {})}
            Summary: {case_data.get('summary', '')}
            """
            
            # Add document to collection
            self.case_collection.add(
                ids=[doc_id],
                documents=[text_for_embedding],
                metadatas=[{
                    'title': case_data.get('title', ''),
                    'citation': case_data.get('citation', ''),
                    'court': case_data.get('court', ''),
                    'date': case_data.get('date', ''),
                    'url': case_data.get('url', '')
                }]
            )
            
            logger.info(f"Added case to vector database with ID: {doc_id}")
            return doc_id
        
        except Exception as e:
            logger.error(f"Error adding case to vector database: {str(e)}")
            return ""
    
    def add_statute(self, statute_data: Dict[str, Any]) -> str:
        """
        Add a statute to the vector database
        
        Args:
            statute_data: Dictionary with statute information
            
        Returns:
            ID of the added statute
        """
        try:
            # Generate an ID if none provided
            doc_id = statute_data.get('id', str(uuid.uuid4()))
            
            # Prepare text for embedding
            text_for_embedding = f"""
            Title: {statute_data.get('title', '')}
            Chapter: {statute_data.get('chapter', '')}
            Summary: {statute_data.get('summary', '')}
            """
            
            # Add document to collection
            self.statute_collection.add(
                ids=[doc_id],
                documents=[text_for_embedding],
                metadatas=[{
                    'title': statute_data.get('title', ''),
                    'chapter': statute_data.get('chapter', ''),
                    'date': statute_data.get('date', ''),
                    'url': statute_data.get('url', '')
                }]
            )
            
            logger.info(f"Added statute to vector database with ID: {doc_id}")
            return doc_id
        
        except Exception as e:
            logger.error(f"Error adding statute to vector database: {str(e)}")
            return ""
    
    def add_document(self, document_data: Dict[str, Any]) -> str:
        """
        Add a legal document to the vector database
        
        Args:
            document_data: Dictionary with document information
            
        Returns:
            ID of the added document
        """
        try:
            # Generate an ID if none provided
            doc_id = document_data.get('id', str(uuid.uuid4()))
            
            # Prepare text for embedding
            text_for_embedding = f"""
            Title: {document_data.get('title', '')}
            Type: {document_data.get('document_type', '')}
            Content: {document_data.get('content', '')}
            """
            
            # Add document to collection
            self.document_collection.add(
                ids=[doc_id],
                documents=[text_for_embedding],
                metadatas=[{
                    'title': document_data.get('title', ''),
                    'document_type': document_data.get('document_type', ''),
                    'status': document_data.get('status', ''),
                    'created_at': document_data.get('created_at', '')
                }]
            )
            
            logger.info(f"Added document to vector database with ID: {doc_id}")
            return doc_id
        
        except Exception as e:
            logger.error(f"Error adding document to vector database: {str(e)}")
            return ""
    
    def add_contract(self, contract_data: Dict[str, Any]) -> str:
        """
        Add a contract to the vector database
        
        Args:
            contract_data: Dictionary with contract information
            
        Returns:
            ID of the added contract
        """
        try:
            # Generate an ID if none provided
            doc_id = contract_data.get('id', str(uuid.uuid4()))
            
            # Prepare text for embedding
            text_for_embedding = f"""
            Title: {contract_data.get('title', '')}
            Type: {contract_data.get('contract_type', '')}
            Content: {contract_data.get('content', '')}
            Key Terms: {contract_data.get('key_terms', '')}
            """
            
            # Add document to collection
            self.contract_collection.add(
                ids=[doc_id],
                documents=[text_for_embedding],
                metadatas=[{
                    'title': contract_data.get('title', ''),
                    'contract_type': contract_data.get('contract_type', ''),
                    'status': contract_data.get('status', ''),
                    'start_date': contract_data.get('start_date', ''),
                    'end_date': contract_data.get('end_date', '')
                }]
            )
            
            logger.info(f"Added contract to vector database with ID: {doc_id}")
            return doc_id
        
        except Exception as e:
            logger.error(f"Error adding contract to vector database: {str(e)}")
            return ""
    
    def search_cases(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for cases semantically similar to the query
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            results = self.case_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results.get('ids'):
                for i, doc_id in enumerate(results['ids'][0]):
                    if i < len(results['metadatas'][0]):
                        metadata = results['metadatas'][0][i]
                        document = results['documents'][0][i] if results.get('documents') else ""
                        
                        formatted_results.append({
                            'id': doc_id,
                            'title': metadata.get('title', ''),
                            'citation': metadata.get('citation', ''),
                            'court': metadata.get('court', ''),
                            'date': metadata.get('date', ''),
                            'url': metadata.get('url', ''),
                            'content': document,
                            'score': results.get('distances', [[]])[0][i] if results.get('distances') else None
                        })
            
            logger.info(f"Found {len(formatted_results)} cases for query: {query}")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error searching cases in vector database: {str(e)}")
            return []
    
    def search_statutes(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for statutes semantically similar to the query
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            results = self.statute_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results.get('ids'):
                for i, doc_id in enumerate(results['ids'][0]):
                    if i < len(results['metadatas'][0]):
                        metadata = results['metadatas'][0][i]
                        document = results['documents'][0][i] if results.get('documents') else ""
                        
                        formatted_results.append({
                            'id': doc_id,
                            'title': metadata.get('title', ''),
                            'chapter': metadata.get('chapter', ''),
                            'date': metadata.get('date', ''),
                            'url': metadata.get('url', ''),
                            'content': document,
                            'score': results.get('distances', [[]])[0][i] if results.get('distances') else None
                        })
            
            logger.info(f"Found {len(formatted_results)} statutes for query: {query}")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error searching statutes in vector database: {str(e)}")
            return []
    
    def search_documents(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents semantically similar to the query
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            results = self.document_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results.get('ids'):
                for i, doc_id in enumerate(results['ids'][0]):
                    if i < len(results['metadatas'][0]):
                        metadata = results['metadatas'][0][i]
                        document = results['documents'][0][i] if results.get('documents') else ""
                        
                        formatted_results.append({
                            'id': doc_id,
                            'title': metadata.get('title', ''),
                            'document_type': metadata.get('document_type', ''),
                            'status': metadata.get('status', ''),
                            'created_at': metadata.get('created_at', ''),
                            'content': document,
                            'score': results.get('distances', [[]])[0][i] if results.get('distances') else None
                        })
            
            logger.info(f"Found {len(formatted_results)} documents for query: {query}")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error searching documents in vector database: {str(e)}")
            return []
    
    def search_contracts(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for contracts semantically similar to the query
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            List of search results
        """
        try:
            results = self.contract_collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            formatted_results = []
            if results.get('ids'):
                for i, doc_id in enumerate(results['ids'][0]):
                    if i < len(results['metadatas'][0]):
                        metadata = results['metadatas'][0][i]
                        document = results['documents'][0][i] if results.get('documents') else ""
                        
                        formatted_results.append({
                            'id': doc_id,
                            'title': metadata.get('title', ''),
                            'contract_type': metadata.get('contract_type', ''),
                            'status': metadata.get('status', ''),
                            'start_date': metadata.get('start_date', ''),
                            'end_date': metadata.get('end_date', ''),
                            'content': document,
                            'score': results.get('distances', [[]])[0][i] if results.get('distances') else None
                        })
            
            logger.info(f"Found {len(formatted_results)} contracts for query: {query}")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Error searching contracts in vector database: {str(e)}")
            return []
    
    def search_all(self, query: str, n_results: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search all collections for the query
        
        Args:
            query: Search query
            n_results: Number of results to return per collection
            
        Returns:
            Dictionary with search results for each collection
        """
        return {
            'cases': self.search_cases(query, n_results),
            'statutes': self.search_statutes(query, n_results),
            'documents': self.search_documents(query, n_results),
            'contracts': self.search_contracts(query, n_results)
        }
    
    def delete_document(self, collection_name: str, doc_id: str) -> bool:
        """
        Delete a document from a collection
        
        Args:
            collection_name: Name of the collection
            doc_id: ID of the document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            collection = self.chroma_client.get_collection(name=collection_name)
            collection.delete(ids=[doc_id])
            logger.info(f"Deleted document {doc_id} from collection {collection_name}")
            return True
        
        except Exception as e:
            logger.error(f"Error deleting document {doc_id} from collection {collection_name}: {str(e)}")
            return False
