import logging
import trafilatura
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
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
            logger.info(f"Fetching case law from {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            cases = []
            
            # Find the document table - based on the HTML structure from the Kenya Law website
            doc_table = soup.select_one('table.doc-table')
            
            if doc_table:
                # Find all table rows that are not the header row
                case_listings = doc_table.select('tbody tr')
                
                # Extract case information from each listing
                count = 0
                for case in case_listings:
                    # Skip if we've reached the limit
                    if count >= limit:
                        break
                    
                    # Skip date grouping rows (these have an id attribute)
                    if case.select_one('td[id]'):
                        continue
                    
                    # Find the title cell and link
                    title_cell = case.select_one('td.cell-title')
                    if title_cell:
                        title_elem = title_cell.select_one('a')
                        
                        if title_elem:
                            title = title_elem.text.strip()
                            href = title_elem.get('href', '')
                            
                            # Normalize the URL
                            if href.startswith('/'):
                                link = urljoin(self.base_url, href)
                            elif href.startswith('http'):
                                link = href
                            else:
                                link = urljoin(self.base_url, '/' + href)
                            
                            # Get metadata - looking for date/court information in the title
                            meta = {}
                            
                            # Extract date from title if present
                            date_match = re.search(r'\((\d+\s+\w+\s+\d{4})\)', title)
                            if date_match:
                                meta['Date'] = date_match.group(1)
                            
                            # Extract case type if present
                            type_match = re.search(r'\((Judgment|Ruling|Advisory Opinion|Order)\)', title)
                            if type_match:
                                meta['Type'] = type_match.group(1)
                            
                            # Extract case number if present
                            case_num_match = re.search(r'\((Petition|Reference|Application|Civil Appeal|Criminal Appeal)\s+[^)]+\)', title)
                            if case_num_match:
                                meta['Case Number'] = case_num_match.group(0).strip('()')
                            
                            # Create case dictionary and add to results
                            cases.append({
                                'title': title,
                                'link': link,
                                'metadata': meta
                            })
                            count += 1
            
            # If no cases found in the table, try alternative selectors
            if not cases:
                # Look for case links in articles
                article_links = soup.select('main#top article a')
                
                count = 0
                for link_elem in article_links:
                    # Skip if we've reached the limit
                    if count >= limit:
                        break
                    
                    # Skip links without text
                    if not link_elem.text.strip():
                        continue
                    
                    # Skip navigation links
                    if link_elem.has_attr('aria-label') or 'nav-link' in link_elem.get('class', []):
                        continue
                    
                    title = link_elem.text.strip()
                    href = link_elem.get('href', '')
                    
                    # Normalize the URL
                    if href.startswith('/'):
                        link = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(self.base_url, '/' + href)
                    
                    # Create case dictionary and add to results
                    cases.append({
                        'title': title,
                        'link': link,
                        'metadata': {}
                    })
                    count += 1
            
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
            logger.info(f"Fetching case details from {case_url}")
            
            # Use trafilatura to get clean text
            downloaded = trafilatura.fetch_url(case_url)
            text_content = trafilatura.extract(downloaded)
            
            # Also get structured data with BeautifulSoup
            response = self.session.get(case_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract case info
            case = {
                'title': '',
                'full_text': text_content or '',
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
            
            # Get the title - try different selectors
            title_elem = soup.select_one('h1')
            if title_elem:
                case['title'] = title_elem.text.strip()
            
            # Get metadata from different possible containers
            meta_sections = [
                soup.select_one('.decision-details'),
                soup.select_one('.case-meta'),
                soup.select_one('.document-metadata'),
                soup.select_one('header')
            ]
            
            for meta_section in meta_sections:
                if meta_section:
                    # Extract all text data from the section
                    section_text = meta_section.text.strip()
                    
                    # Look for common patterns in the text
                    if 'Citation' in section_text:
                        citation_match = re.search(r'Citation:?\s*([^\n]+)', section_text)
                        if citation_match:
                            case['citation'] = citation_match.group(1).strip()
                    
                    if 'Court' in section_text:
                        court_match = re.search(r'Court:?\s*([^\n]+)', section_text)
                        if court_match:
                            case['court'] = court_match.group(1).strip()
                    
                    if 'Judge' in section_text or 'Coram' in section_text:
                        judge_match = re.search(r'(?:Judge|Coram):?\s*([^\n]+)', section_text)
                        if judge_match:
                            judges_text = judge_match.group(1).strip()
                            case['judges'] = [j.strip() for j in re.split(r',|;', judges_text)]
                    
                    if 'Date' in section_text:
                        date_match = re.search(r'Date:?\s*([^\n]+)', section_text)
                        if date_match:
                            case['date'] = date_match.group(1).strip()
            
            # Try to extract parties from structured data or the title
            if 'v' in case['title'] or 'vs' in case['title'].lower():
                parties_match = re.search(r'([^v]+)\s+v\.?\s+([^(]+)', case['title'], re.IGNORECASE)
                if parties_match:
                    case['parties']['applicant'] = parties_match.group(1).strip()
                    case['parties']['respondent'] = parties_match.group(2).strip()
            
            # Extract ruling content (main text of the judgment)
            main_content = soup.select_one('main') or soup.select_one('article') or soup.select_one('.document-content')
            if main_content:
                ruling_text = main_content.text.strip()
                # Remove any headers or metadata from the start
                ruling_text = re.sub(r'^.*?(?:JUDGMENT|RULING)', 'JUDGMENT', ruling_text, flags=re.DOTALL)
                case['ruling'] = ruling_text
            else:
                # If we can't find structured content, use the trafilatura extracted text
                case['ruling'] = text_content
            
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
            logger.info(f"Searching for cases with query: {query}")
            response = self.session.get(url, params={
                'q': query,
                'page': page
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Try multiple potential selectors for search results
            result_items = soup.select('.search-list-item')
            if not result_items:
                result_items = soup.select('.search-result-item')
            if not result_items:
                result_items = soup.select('.document-list-item')
            if not result_items:
                result_items = soup.select('article')
            
            for item in result_items:
                # Try to find title and link
                title_elem = None
                for selector in ['h3 a', 'h4 a', '.document-title a', 'a.document-title', 'a.title']:
                    if title_elem is None:
                        title_elem = item.select_one(selector)
                
                # If still not found, try any link with content
                if title_elem is None:
                    links = item.select('a')
                    for a in links:
                        if a.text.strip() and not a.get('class') and not a.has_attr('aria-label'):
                            title_elem = a
                            break
                
                if title_elem:
                    title = title_elem.text.strip()
                    href = title_elem.get('href', '')
                    
                    # Normalize the URL
                    if href.startswith('/'):
                        link = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(self.base_url, '/' + href)
                    
                    # Get snippet or excerpt
                    excerpt = ''
                    excerpt_elem = None
                    for selector in ['.search-snippet', '.excerpt', '.summary', 'p']:
                        if excerpt_elem is None:
                            excerpt_elem = item.select_one(selector)
                    
                    if excerpt_elem:
                        excerpt = excerpt_elem.text.strip()
                    
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
            logger.info(f"Fetching legislation from {url}")
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            legislation = []
            
            # Try multiple potential selectors for legislation listings
            legislation_items = []
            for selector in ['.legislation-item', '.document-list-item', 'article']:
                if not legislation_items:
                    legislation_items = soup.select(selector)
            
            count = 0
            for item in legislation_items:
                # Skip if we've reached the limit
                if count >= limit:
                    break
                
                # Try to find title and link
                title_elem = None
                for selector in ['h3 a', 'h4 a', '.legislation-title a', 'a.title']:
                    if title_elem is None:
                        title_elem = item.select_one(selector)
                
                # If still not found, try any link with content
                if title_elem is None:
                    links = item.select('a')
                    for a in links:
                        if a.text.strip() and not a.has_attr('aria-label'):
                            title_elem = a
                            break
                
                if title_elem:
                    title = title_elem.text.strip()
                    href = title_elem.get('href', '')
                    
                    # Normalize the URL
                    if href.startswith('/'):
                        link = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(self.base_url, '/' + href)
                    
                    legislation.append({
                        'title': title,
                        'link': link
                    })
                    count += 1
            
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
            logger.info(f"Fetching legislation details from {legislation_url}")
            
            # Use trafilatura to get clean text
            downloaded = trafilatura.fetch_url(legislation_url)
            text_content = trafilatura.extract(downloaded)
            
            # Also get structured data with BeautifulSoup
            response = self.session.get(legislation_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract legislation info
            legislation = {
                'title': '',
                'full_text': text_content or '',
                'chapters': [],
                'date': '',
                'url': legislation_url
            }
            
            # Get the title - try different selectors
            title_elem = soup.select_one('h1')
            if title_elem:
                legislation['title'] = title_elem.text.strip()
            
            # Try to extract date information
            date_elem = soup.select_one('.date') or soup.select_one('.meta-date')
            if date_elem:
                legislation['date'] = date_elem.text.strip()
            
            # Try to extract chapters or sections
            chapter_items = []
            for selector in ['.chapter', '.section', 'article.section', '.document-section']:
                if not chapter_items:
                    chapter_items = soup.select(selector)
            
            # If no structured chapters found, try to parse the main content
            if not chapter_items:
                main_content = soup.select_one('main') or soup.select_one('article')
                if main_content:
                    # Look for headings as chapter/section markers
                    headings = main_content.select('h2, h3')
                    for heading in headings:
                        title = heading.text.strip()
                        content = ''
                        
                        # Get content until next heading
                        current = heading.next_sibling
                        while current and not (current.name in ['h2', 'h3']):
                            if current.name and current.text.strip():
                                content += current.text.strip() + '\n'
                            current = current.next_sibling
                        
                        legislation['chapters'].append({
                            'title': title,
                            'content': content.strip()
                        })
            else:
                # Process found chapter items
                for chapter in chapter_items:
                    title_elem = chapter.select_one('h2') or chapter.select_one('h3') or chapter.select_one('.title')
                    content_elem = chapter.select_one('.content') or chapter
                    
                    if title_elem and content_elem:
                        title = title_elem.text.strip()
                        content = content_elem.text.strip()
                        
                        # Remove the title from the content if it's included
                        content = content.replace(title, '').strip()
                        
                        legislation['chapters'].append({
                            'title': title,
                            'content': content
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
            logger.info(f"Extracting text content from {url}")
            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded)
            return text
        except Exception as e:
            logger.error(f"Error extracting text content from {url}: {str(e)}")
            return None
