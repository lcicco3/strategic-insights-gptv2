"""
Vector database service for Strategic Insights GPT Backend
"""

import os
from typing import List, Dict, Any, Optional
import logging
from pinecone import Pinecone
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class VectorService:
    """Service for vector database operations using Pinecone"""
    
    def __init__(self):
        self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
        self.pinecone_environment = os.getenv('PINECONE_ENVIRONMENT', 'us-east-1')
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'rweproposalstrategy')
        
        # Initialize Pinecone
        if self.pinecone_api_key:
            try:
                self.pc = Pinecone(api_key=self.pinecone_api_key)
                self.index = self.pc.Index(self.index_name)
                logger.info(f"Connected to Pinecone index: {self.index_name}")
            except Exception as e:
                logger.error(f"Failed to connect to Pinecone: {str(e)}")
                self.pc = None
                self.index = None
        else:
            logger.warning("Pinecone API key not provided")
            self.pc = None
            self.index = None
        
        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(
            model=os.getenv('OPENAI_MODEL', 'text-embedding-3-small')
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
    
    def similarity_search(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Perform similarity search in vector database"""
        try:
            if not self.index:
                logger.error("Pinecone index not available")
                return []
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Perform search
            search_params = {
                'vector': query_embedding,
                'top_k': k,
                'include_metadata': True
            }
            
            if filter_dict:
                search_params['filter'] = filter_dict
            
            results = self.index.query(**search_params)
            
            # Format results
            formatted_results = []
            for match in results.get('matches', []):
                formatted_results.append({
                    'id': match.get('id'),
                    'score': match.get('score'),
                    'metadata': match.get('metadata', {}),
                    'content': match.get('metadata', {}).get('content', '')
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return []
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Add documents to vector database"""
        try:
            if not self.index:
                logger.error("Pinecone index not available")
                return False
            
            vectors_to_upsert = []
            
            for doc in documents:
                # Extract text content
                content = self._extract_content(doc)
                
                # Split into chunks
                chunks = self.text_splitter.split_text(content)
                
                for i, chunk in enumerate(chunks):
                    # Generate embedding
                    embedding = self.embeddings.embed_query(chunk)
                    
                    # Create vector ID
                    vector_id = f"{doc.get('id', 'unknown')}_{i}"
                    
                    # Prepare metadata
                    metadata = {
                        'content': chunk,
                        'source': doc.get('source', 'unknown'),
                        'title': doc.get('title', ''),
                        'chunk_index': i,
                        'total_chunks': len(chunks)
                    }
                    
                    # Add document-specific metadata
                    if doc.get('pmid'):
                        metadata['pmid'] = doc['pmid']
                    if doc.get('nct_id'):
                        metadata['nct_id'] = doc['nct_id']
                    if doc.get('journal'):
                        metadata['journal'] = doc['journal']
                    if doc.get('authors'):
                        metadata['authors'] = ', '.join(doc['authors'][:3])  # First 3 authors
                    
                    vectors_to_upsert.append({
                        'id': vector_id,
                        'values': embedding,
                        'metadata': metadata
                    })
            
            # Upsert vectors in batches
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"Successfully added {len(vectors_to_upsert)} vectors to index")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents to vector database: {str(e)}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector index"""
        try:
            if not self.index:
                return {'error': 'Pinecone index not available'}
            
            stats = self.index.describe_index_stats()
            return {
                'total_vectors': stats.get('total_vector_count', 0),
                'dimension': stats.get('dimension', 0),
                'index_fullness': stats.get('index_fullness', 0),
                'namespaces': stats.get('namespaces', {})
            }
            
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {'error': str(e)}
    
    def _extract_content(self, doc: Dict[str, Any]) -> str:
        """Extract text content from document for embedding"""
        content_parts = []
        
        # Add title
        if doc.get('title'):
            content_parts.append(f"Title: {doc['title']}")
        
        # Add abstract or summary
        if doc.get('abstract'):
            content_parts.append(f"Abstract: {doc['abstract']}")
        elif doc.get('brief_summary'):
            content_parts.append(f"Summary: {doc['brief_summary']}")
        
        # Add detailed description for clinical trials
        if doc.get('detailed_description'):
            content_parts.append(f"Description: {doc['detailed_description']}")
        
        # Add conditions for clinical trials
        if doc.get('conditions'):
            conditions = ', '.join(doc['conditions'])
            content_parts.append(f"Conditions: {conditions}")
        
        # Add interventions for clinical trials
        if doc.get('interventions'):
            interventions = []
            for intervention in doc['interventions']:
                if isinstance(intervention, dict):
                    interventions.append(f"{intervention.get('type', '')}: {intervention.get('name', '')}")
                else:
                    interventions.append(str(intervention))
            content_parts.append(f"Interventions: {', '.join(interventions)}")
        
        # Add journal for PubMed articles
        if doc.get('journal'):
            content_parts.append(f"Journal: {doc['journal']}")
        
        # Add authors for PubMed articles
        if doc.get('authors'):
            authors = ', '.join(doc['authors'][:5])  # First 5 authors
            content_parts.append(f"Authors: {authors}")
        
        return '\n\n'.join(content_parts)

