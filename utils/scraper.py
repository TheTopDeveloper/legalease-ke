import logging
import trafilatura
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
from config import KENYALAW_BASE_URL

logger = logging.getLogger(__name__)

class KenyaLawScraper:
    """
    Scraper for retrieving legal content from new.kenyalaw.org
    """
    
    def __init__(self, base_url=KENYALAW_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_case_law(self, court_code, page=1, limit=10):
        """
        Retrieve case law listings from a specific court
        
        Args:
            court_code: Court code (e.g., 'KESC', 'KECA', 'KEHC')
            page: Page number for pagination
            limit: Number of results per page
            
        Returns:
            List of case summaries with links
        """
        url = f"{self.base_url}/judgments/{court_code}/?page={page}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            cases = []
            
            # Extract case listings
            case_listings = soup.select('.cases-list .case-item')
            for case in case_listings[:limit]:
                title_elem = case.select_one('.case-title a')
                if title_elem:
                    title = title_elem.text.strip()
                    link = urljoin(self.base_url, title_elem['href'])
                    
                    # Get metadata
                    meta = {}
                    meta_elems = case.select('.case-meta .meta-item')
                    for elem in meta_elems:
                        label = elem.select_one('.meta-label')
                        value = elem.select_one('.meta-value')
                        if label and value:
                            meta[label.text.strip()] = value.text.strip()
                    
                    cases.append({
                        'title': title,
                        'link': link,
                        'metadata': meta
                    })
            
            return cases
        
        except Exception as e:
            logger.error(f"Error retrieving case law for court {court_code}: {str(e)}")
            return []
    
    def get_case_details(self, case_url):
        """
        Retrieve full details of a specific case
        
        Args:
            case_url: URL of the case
            
        Returns:
            Dict containing case details
        """
        try:
            # Use trafilatura to get clean text
            downloaded = trafilatura.fetch_url(case_url)
            text_content = trafilatura.extract(downloaded)
            
            # Also get structured data with BeautifulSoup
            response = self.session.get(case_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract case info
            case = {
                'title': soup.select_one('h1.case-title').text.strip() if soup.select_one('h1.case-title') else '',
                'full_text': text_content,
                'citation': '',
                'court': '',
                'judges': [],
                'date': '',
                'parties': {
                    'applicant': '',
                    'respondent': ''
                },
                'ruling': '',
                'url': case_url
            }
            
            # Extract meta information
            meta_section = soup.select_one('.case-details')
            if meta_section:
                for item in meta_section.select('.meta-item'):
                    label = item.select_one('.meta-label')
                    value = item.select_one('.meta-value')
                    if label and value:
                        label_text = label.text.strip().lower()
                        value_text = value.text.strip()
                        
                        if 'citation' in label_text:
                            case['citation'] = value_text
                        elif 'court' in label_text:
                            case['court'] = value_text
                        elif 'judge' in label_text or 'coram' in label_text:
                            case['judges'] = [j.strip() for j in value_text.split(',')]
                        elif 'date' in label_text:
                            case['date'] = value_text
            
            # Extract parties
            parties_section = soup.select_one('.case-parties')
            if parties_section:
                applicant = parties_section.select_one('.applicant')
                respondent = parties_section.select_one('.respondent')
                
                if applicant:
                    case['parties']['applicant'] = applicant.text.strip()
                if respondent:
                    case['parties']['respondent'] = respondent.text.strip()
            
            # Extract ruling content (this is approximate)
            ruling_section = soup.select_one('.judgment-text')
            if ruling_section:
                case['ruling'] = ruling_section.text.strip()
            
            return case
        
        except Exception as e:
            logger.error(f"Error retrieving case details for {case_url}: {str(e)}")
            return None
    
    def search_cases(self, query, page=1):
        """
        Search for cases using the search functionality
        
        Args:
            query: Search query
            page: Page number for pagination
            
        Returns:
            List of search results
        """
        url = f"{self.base_url}/search/"
        
        try:
            response = self.session.get(url, params={
                'q': query,
                'page': page
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Extract search results
            result_items = soup.select('.search-results .search-item')
            for item in result_items:
                title_elem = item.select_one('.search-title a')
                
                if title_elem:
                    title = title_elem.text.strip()
                    link = urljoin(self.base_url, title_elem['href'])
                    
                    # Get snippet or excerpt
                    snippet = item.select_one('.search-snippet')
                    excerpt = snippet.text.strip() if snippet else ''
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'excerpt': excerpt
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching cases with query '{query}': {str(e)}")
            return []
    
    def get_legislation(self, limit=10):
        """
        Retrieve legislation listings
        
        Args:
            limit: Number of results to retrieve
            
        Returns:
            List of legislation with links
        """
        url = f"{self.base_url}/legislation/"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            legislation = []
            
            # Extract legislation listings
            legislation_items = soup.select('.legislation-list .legislation-item')
            for item in legislation_items[:limit]:
                title_elem = item.select_one('.legislation-title a')
                
                if title_elem:
                    title = title_elem.text.strip()
                    link = urljoin(self.base_url, title_elem['href'])
                    
                    legislation.append({
                        'title': title,
                        'link': link
                    })
            
            return legislation
        
        except Exception as e:
            logger.error(f"Error retrieving legislation: {str(e)}")
            return []
    
    def get_legislation_details(self, legislation_url):
        """
        Retrieve full details of a specific legislation
        
        Args:
            legislation_url: URL of the legislation
            
        Returns:
            Dict containing legislation details
        """
        try:
            # Use trafilatura to get clean text
            downloaded = trafilatura.fetch_url(legislation_url)
            text_content = trafilatura.extract(downloaded)
            
            # Also get structured data with BeautifulSoup
            response = self.session.get(legislation_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract legislation info
            legislation = {
                'title': soup.select_one('h1.legislation-title').text.strip() if soup.select_one('h1.legislation-title') else '',
                'full_text': text_content,
                'chapters': [],
                'date': '',
                'url': legislation_url
            }
            
            # Extract chapters or sections
            chapter_items = soup.select('.legislation-chapters .chapter-item')
            for chapter in chapter_items:
                title = chapter.select_one('.chapter-title')
                content = chapter.select_one('.chapter-content')
                
                if title and content:
                    legislation['chapters'].append({
                        'title': title.text.strip(),
                        'content': content.text.strip()
                    })
            
            return legislation
        
        except Exception as e:
            logger.error(f"Error retrieving legislation details for {legislation_url}: {str(e)}")
            return None
    
    def get_website_text_content(self, url):
        """
        Get the main text content of a webpage using trafilatura
        
        Args:
            url: URL of the webpage
            
        Returns:
            Extracted text content
        """
        try:
            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded)
            return text
        except Exception as e:
            logger.error(f"Error extracting text content from {url}: {str(e)}")
            return None
