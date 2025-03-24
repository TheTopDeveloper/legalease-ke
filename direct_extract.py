"""
Direct data extraction script for Kenya Law website.
This script extracts data directly from the HTML and saves it for analysis.
"""
import requests
from bs4 import BeautifulSoup
import json
import os
from config import KENYALAW_BASE_URL, COURT_LEVELS

def extract_and_save_html(url, output_file):
    """Extract HTML from a URL and save it to a file"""
    print(f"Fetching {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch {url}: Status code {response.status_code}")
        return None
    
    print(f"Successfully fetched {url} ({len(response.text)} bytes)")
    
    # Save raw HTML
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(response.text)
    
    return response.text

def extract_document_list(html, output_file):
    """Extract document listings from HTML and save as JSON"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Get all document list items (try various selectors)
    document_items = []
    
    # Save all links for analysis
    links = []
    for a in soup.find_all('a', href=True):
        if a.text.strip():
            links.append({
                'text': a.text.strip(),
                'href': a.get('href'),
                'classes': a.get('class', []),
                'parent_classes': a.parent.get('class', []) if a.parent else [],
                'grandparent_classes': a.parent.parent.get('class', []) if a.parent and a.parent.parent else []
            })
    
    # Save the link data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(links, f, indent=2)
    
    print(f"Extracted {len(links)} links to {output_file}")
    return links

def main():
    """Main function"""
    # Create output directory if it doesn't exist
    os.makedirs('data_extracted', exist_ok=True)
    
    # Extract Supreme Court judgments
    court_code = COURT_LEVELS["Supreme Court"]
    url = f"{KENYALAW_BASE_URL}/judgments/{court_code}/"
    html = extract_and_save_html(url, 'data_extracted/supreme_court.html')
    if html:
        extract_document_list(html, 'data_extracted/supreme_court_links.json')
    
    # Extract search results
    search_query = "constitutional rights"
    search_url = f"{KENYALAW_BASE_URL}/search/?q={search_query.replace(' ', '+')}"
    html = extract_and_save_html(search_url, 'data_extracted/search_results.html')
    if html:
        extract_document_list(html, 'data_extracted/search_links.json')
    
    # Extract legislation
    legislation_url = f"{KENYALAW_BASE_URL}/legislation/"
    html = extract_and_save_html(legislation_url, 'data_extracted/legislation.html')
    if html:
        extract_document_list(html, 'data_extracted/legislation_links.json')
    
    print("\nExtraction complete. Files saved to 'data_extracted' directory.")

if __name__ == "__main__":
    main()