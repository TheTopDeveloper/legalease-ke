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
            
            # Direct approach: Extract all links in cells with cell-title class
            case_links = soup.select('td.cell-title a')
            if case_links:
                logger.info(f"Found {len(case_links)} case links using td.cell-title a selector")
                count = 0
                for link_elem in case_links:
                    # Skip if we've reached the limit
                    if count >= limit:
                        break
                    
                    # Get title and URL
                    title = link_elem.text.strip()
                    href = link_elem.get('href', '')
                    
                    # Skip empty links or navigation
                    if not title or not href:
                        continue
                    
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
            
            # If no cases found, look for all links that point to judgment URLs
            if not cases:
                # Get all links on the page
                all_links = soup.find_all('a')
                judgment_links = [link for link in all_links if link.get('href') and 
                                  ('/judgment/' in link.get('href') or 
                                   '/akn/ke/judgment/' in link.get('href'))]
                
                logger.info(f"Found {len(judgment_links)} judgment links by URL pattern")
                count = 0
                for link_elem in judgment_links:
                    # Skip if we've reached the limit
                    if count >= limit:
                        break
                    
                    # Skip links without text or with very short text
                    title = link_elem.text.strip()
                    if len(title) < 15:  # Skip very short titles, likely navigation
                        continue
                    
                    href = link_elem.get('href', '')
                    
                    # Normalize the URL
                    if href.startswith('/'):
                        link = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(self.base_url, '/' + href)
                    
                    # Get metadata from title if available
                    meta = {}
                    
                    # Extract date from title if present
                    date_match = re.search(r'\b(\d{1,2}\s+\w+\s+\d{4})\b', title)
                    if date_match:
                        meta['Date'] = date_match.group(1)
                    
                    # Extract case number if present
                    case_num_match = re.search(r'\b(Petition|Reference|Application|Civil Appeal|Criminal Appeal)\s+No\.\s+\d+\s+of\s+\d{4}\b', title)
                    if case_num_match:
                        meta['Case Number'] = case_num_match.group(0)
                    
                    # Create case dictionary and add to results
                    cases.append({
                        'title': title,
                        'link': link,
                        'metadata': meta
                    })
                    count += 1
            
            # Last resort: find any links with "KLR" in the text, which indicates Kenya Law Reports
            if not cases:
                klr_links = [link for link in soup.find_all('a') if 'KLR' in link.text]
                
                logger.info(f"Found {len(klr_links)} KLR links as last resort")
                count = 0
                for link_elem in klr_links:
                    # Skip if we've reached the limit
                    if count >= limit:
                        break
                    
                    title = link_elem.text.strip()
                    href = link_elem.get('href', '')
                    
                    # Normalize the URL
                    if href.startswith('/'):
                        link = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(self.base_url, '/' + href)
                    
                    # Create case dictionary and add to results (minimal metadata)
                    cases.append({
                        'title': title,
                        'link': link,
                        'metadata': {}
                    })
                    count += 1
            
            # Print debug information
            if cases:
                logger.info(f"Successfully extracted {len(cases)} cases")
            else:
                logger.warning("No cases found on the page")
                # Save HTML for debugging
                with open('debug_output.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                logger.info("Saved HTML to debug_output.html for inspection")
            
            return cases
        
        except Exception as e:
            logger.error(f"Error retrieving case law for court {court_code}: {str(e)}")
            # Log the traceback for debugging
            import traceback
            logger.error(traceback.format_exc())
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
            
            # First approach: Look for links in search result containers
            result_items = []
            for selector in ['.search-list-item', '.search-result-item', '.document-list-item', 'article']:
                if not result_items:
                    result_items = soup.select(selector)
            
            logger.info(f"Found {len(result_items)} search result items with container selectors")
            
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
                        if a.text.strip() and not a.has_attr('aria-label'):
                            title_elem = a
                            break
                
                if title_elem:
                    title = title_elem.text.strip()
                    href = title_elem.get('href', '')
                    
                    # Skip irrelevant links
                    if not href or href == '#' or 'javascript:' in href:
                        continue
                    
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
            
            # Alternative approach: look for all links that point to judgment URLs
            if not results:
                logger.info("No results found with container selectors, trying URL pattern approach")
                all_links = soup.find_all('a')
                judgment_links = [link for link in all_links if link.get('href') and 
                                ('/judgment/' in link.get('href') or 
                                '/akn/ke/judgment/' in link.get('href'))]
                
                logger.info(f"Found {len(judgment_links)} judgment links by URL pattern")
                for link_elem in judgment_links[:10]:  # Limit to first 10 results
                    title = link_elem.text.strip()
                    if len(title) < 15:  # Skip very short titles, likely navigation
                        continue
                        
                    href = link_elem.get('href', '')
                    
                    # Normalize the URL
                    if href.startswith('/'):
                        link = urljoin(self.base_url, href)
                    elif href.startswith('http'):
                        link = href
                    else:
                        link = urljoin(self.base_url, '/' + href)
                    
                    # Get parent element to look for excerpt
                    parent = link_elem.parent
                    excerpt = ''
                    
                    # Try to find paragraph text near the link
                    if parent:
                        sibling = parent.find_next_sibling('p')
                        if sibling:
                            excerpt = sibling.text.strip()
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'excerpt': excerpt
                    })
            
            # If still no results, look for any content with the search term
            if not results:
                logger.info("No results found with URL patterns, searching for content with query term")
                paragraphs = soup.find_all('p')
                
                potential_results = []
                for p in paragraphs:
                    if query.lower() in p.text.lower():
                        # Find nearby links
                        nearby_links = []
                        
                        # Check siblings
                        prev_sibling = p.find_previous_sibling()
                        if prev_sibling:
                            nearby_links.extend(prev_sibling.find_all('a'))
                            
                        next_sibling = p.find_next_sibling()
                        if next_sibling:
                            nearby_links.extend(next_sibling.find_all('a'))
                            
                        # Check parent's siblings
                        if p.parent:
                            prev_parent_sibling = p.parent.find_previous_sibling()
                            if prev_parent_sibling:
                                nearby_links.extend(prev_parent_sibling.find_all('a'))
                                
                            next_parent_sibling = p.parent.find_next_sibling()
                            if next_parent_sibling:
                                nearby_links.extend(next_parent_sibling.find_all('a'))
                        
                        # Also check links inside the paragraph
                        nearby_links.extend(p.find_all('a'))
                        
                        for link in nearby_links:
                            title = link.text.strip()
                            href = link.get('href', '')
                            
                            if not title or not href or href == '#' or 'javascript:' in href:
                                continue
                                
                            # Normalize the URL
                            if href.startswith('/'):
                                result_link = urljoin(self.base_url, href)
                            elif href.startswith('http'):
                                result_link = href
                            else:
                                result_link = urljoin(self.base_url, '/' + href)
                                
                            potential_results.append({
                                'title': title,
                                'link': result_link,
                                'excerpt': p.text.strip(),
                                'relevance': len(p.text)  # Sort by length of text
                            })
                
                # Sort by relevance (length of excerpt)
                potential_results.sort(key=lambda x: x['relevance'], reverse=True)
                
                # Take top 5 results
                for result in potential_results[:5]:
                    del result['relevance']
                    results.append(result)
            
            # Final debug information
            if results:
                logger.info(f"Successfully extracted {len(results)} search results")
            else:
                logger.warning(f"No search results found for query: {query}")
                # Save HTML for debugging
                with open('search_debug.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                logger.info("Saved HTML to search_debug.html for inspection")
            
            return results
        
        except Exception as e:
            logger.error(f"Error searching cases with query '{query}': {str(e)}")
            # Log the traceback for debugging
            import traceback
            logger.error(traceback.format_exc())
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
            
            # Direct approach: Look for links in table cells with cell-title class (similar to cases)
            legislation_links = soup.select('td.cell-title a')
            if legislation_links:
                logger.info(f"Found {len(legislation_links)} legislation links using td.cell-title a selector")
                count = 0
                for link_elem in legislation_links:
                    # Skip if we've reached the limit
                    if count >= limit:
                        break
                    
                    # Get title and URL
                    title = link_elem.text.strip()
                    href = link_elem.get('href', '')
                    
                    # Skip empty links or navigation
                    if not title or not href:
                        continue
                    
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
            
            # If no links found with that approach, try traditional container selectors
            if not legislation:
                # Try multiple potential selectors for legislation listings
                legislation_items = []
                for selector in ['.legislation-item', '.document-list-item', 'article']:
                    if not legislation_items:
                        legislation_items = soup.select(selector)
                
                logger.info(f"Found {len(legislation_items)} legislation items with container selectors")
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
                        
                        # Skip irrelevant links
                        if not href or href == '#' or 'javascript:' in href:
                            continue
                        
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
            
            # If still no results, look for all links that might be legislation
            if not legislation:
                # Get all links on the page
                all_links = soup.find_all('a')
                # Look for links with legislation-related path or text
                legislation_links = [link for link in all_links if link.get('href') and 
                                    ('/akn/ke/act/' in link.get('href') or 
                                     '/legislation/' in link.get('href') or
                                     'Act' in link.text or 
                                     'Constitution' in link.text)]
                
                logger.info(f"Found {len(legislation_links)} legislation links by URL pattern or keyword")
                count = 0
                for link_elem in legislation_links:
                    # Skip if we've reached the limit
                    if count >= limit:
                        break
                    
                    # Skip links without text or with very short text
                    title = link_elem.text.strip()
                    if len(title) < 5:  # Skip very short titles, likely navigation
                        continue
                        
                    href = link_elem.get('href', '')
                    
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
            
            # Print debug information
            if legislation:
                logger.info(f"Successfully extracted {len(legislation)} legislation items")
            else:
                logger.warning("No legislation found on the page")
                # Save HTML for debugging
                with open('legislation_debug.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                logger.info("Saved HTML to legislation_debug.html for inspection")
            
            return legislation
        
        except Exception as e:
            logger.error(f"Error retrieving legislation: {str(e)}")
            # Log the traceback for debugging
            import traceback
            logger.error(traceback.format_exc())
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
