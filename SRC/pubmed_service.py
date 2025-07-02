"""
PubMed API service for Strategic Insights GPT Backend
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class PubMedService:
    """Service for interacting with PubMed/NCBI E-utilities API"""
    
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.email = os.getenv('PUBMED_EMAIL')
        self.api_key = os.getenv('PUBMED_API_KEY')
        
        # Strategic queries for RWE research
        self.strategic_queries = [
            "real-world evidence AND registry",
            "cost-effectiveness AND real-world evidence",
            "patient-reported outcomes AND real-world evidence",
            "comparative effectiveness research AND real-world data",
            "real-world evidence AND regulatory approval",
            "observational study AND real-world evidence",
            "real-world evidence AND clinical trials",
            "health economics AND real-world evidence",
            "real-world evidence AND drug safety",
            "real-world evidence AND treatment effectiveness",
            "real-world evidence AND healthcare utilization",
            "real-world evidence AND patient outcomes"
        ]
    
    def search_articles(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search PubMed articles by query"""
        try:
            # Step 1: Search for PMIDs
            search_url = f"{self.base_url}/esearch.fcgi"
            search_params = {
                'db': 'pubmed',
                'term': query,
                'retmax': max_results,
                'retmode': 'xml',
                'email': self.email,
                'api_key': self.api_key
            }
            
            response = requests.get(search_url, params=search_params)
            response.raise_for_status()
            
            # Parse search results
            root = ET.fromstring(response.content)
            pmids = [id_elem.text for id_elem in root.findall('.//Id')]
            
            if not pmids:
                return []
            
            # Step 2: Fetch article details
            return self._fetch_article_details(pmids)
            
        except Exception as e:
            logger.error(f"Error searching PubMed: {str(e)}")
            return []
    
    def bulk_strategic_search(self, topic: str, max_results_per_query: int = 5) -> List[Dict[str, Any]]:
        """Perform bulk strategic search using predefined queries"""
        all_results = []
        
        for query in self.strategic_queries:
            try:
                # Combine topic with strategic query
                full_query = f"{topic} AND ({query})"
                results = self.search_articles(full_query, max_results_per_query)
                
                # Add query context to results
                for result in results:
                    result['search_query'] = query
                    result['topic'] = topic
                
                all_results.extend(results)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in strategic query '{query}': {str(e)}")
                continue
        
        # Remove duplicates based on PMID
        seen_pmids = set()
        unique_results = []
        for result in all_results:
            pmid = result.get('pmid')
            if pmid and pmid not in seen_pmids:
                seen_pmids.add(pmid)
                unique_results.append(result)
        
        return unique_results
    
    def _fetch_article_details(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """Fetch detailed article information for given PMIDs"""
        try:
            fetch_url = f"{self.base_url}/efetch.fcgi"
            fetch_params = {
                'db': 'pubmed',
                'id': ','.join(pmids),
                'retmode': 'xml',
                'email': self.email,
                'api_key': self.api_key
            }
            
            response = requests.get(fetch_url, params=fetch_params)
            response.raise_for_status()
            
            # Parse article details
            root = ET.fromstring(response.content)
            articles = []
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    article_data = self._parse_article(article)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    logger.error(f"Error parsing article: {str(e)}")
                    continue
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching article details: {str(e)}")
            return []
    
    def _parse_article(self, article_elem) -> Dict[str, Any]:
        """Parse individual article XML element"""
        try:
            # Extract PMID
            pmid_elem = article_elem.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else None
            
            # Extract title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "No title available"
            
            # Extract abstract
            abstract_elem = article_elem.find('.//AbstractText')
            abstract = abstract_elem.text if abstract_elem is not None else "No abstract available"
            
            # Extract authors
            authors = []
            for author in article_elem.findall('.//Author'):
                lastname = author.find('.//LastName')
                forename = author.find('.//ForeName')
                if lastname is not None and forename is not None:
                    authors.append(f"{forename.text} {lastname.text}")
            
            # Extract journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None else "Unknown journal"
            
            # Extract publication date
            pub_date = self._extract_publication_date(article_elem)
            
            # Extract DOI
            doi_elem = article_elem.find('.//ArticleId[@IdType="doi"]')
            doi = doi_elem.text if doi_elem is not None else None
            
            return {
                'pmid': pmid,
                'title': title,
                'abstract': abstract,
                'authors': authors,
                'journal': journal,
                'publication_date': pub_date,
                'doi': doi,
                'source': 'pubmed',
                'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
            }
            
        except Exception as e:
            logger.error(f"Error parsing article element: {str(e)}")
            return None
    
    def _extract_publication_date(self, article_elem) -> str:
        """Extract publication date from article element"""
        try:
            # Try to get date from PubDate
            pub_date = article_elem.find('.//PubDate')
            if pub_date is not None:
                year = pub_date.find('.//Year')
                month = pub_date.find('.//Month')
                day = pub_date.find('.//Day')
                
                date_parts = []
                if year is not None:
                    date_parts.append(year.text)
                if month is not None:
                    date_parts.append(month.text)
                if day is not None:
                    date_parts.append(day.text)
                
                return '-'.join(date_parts) if date_parts else "Unknown date"
            
            return "Unknown date"
            
        except Exception:
            return "Unknown date"

