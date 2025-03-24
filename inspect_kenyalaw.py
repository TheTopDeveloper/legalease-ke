"""
Script to inspect the actual HTML structure of the Kenya Law website.
"""
import requests
from bs4 import BeautifulSoup
from config import KENYALAW_BASE_URL

def inspect_webpage(url, output_file="page_structure.txt"):
    """
    Fetch a webpage and save its structure to a file for inspection
    
    Args:
        url: URL to inspect
        output_file: File to save the structure to
    """
    print(f"Fetching {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch {url}: Status code {response.status_code}")
        return
    
    print(f"Successfully fetched {url} ({len(response.text)} bytes)")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Output structure information
    with open(output_file, 'w') as f:
        # Get page title
        f.write(f"Page Title: {soup.title.string if soup.title else 'No title'}\n\n")
        
        # List all div classes
        f.write("=== DIV CLASSES ===\n")
        for div in soup.find_all('div', class_=True):
            f.write(f"{div.get('class')}\n")
        
        # List all heading elements
        f.write("\n=== HEADING ELEMENTS ===\n")
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                f.write(f"h{i}: {heading.get_text().strip()}\n")
        
        # List major sections
        f.write("\n=== MAJOR SECTIONS ===\n")
        for section in soup.find_all(['section', 'main', 'article']):
            section_id = section.get('id', '')
            section_class = ' '.join(section.get('class', []))
            section_title = section.find(['h1', 'h2', 'h3', 'h4'])
            section_title_text = section_title.get_text().strip() if section_title else 'No title'
            
            f.write(f"Section: {section.name} - ID: {section_id} - Class: {section_class} - Title: {section_title_text}\n")
        
        # List all links
        f.write("\n=== FIRST 20 LINKS ===\n")
        for i, link in enumerate(soup.find_all('a', href=True)):
            if i >= 20:
                break
            href = link.get('href')
            text = link.get_text().strip()
            f.write(f"Link: {text} - URL: {href}\n")
    
    print(f"Structure information saved to {output_file}")

def main():
    """Main function"""
    # Inspect Supreme Court judgment listing
    inspect_webpage(f"{KENYALAW_BASE_URL}/judgments/KESC/", "supreme_court_structure.txt")
    
    # Inspect search page
    inspect_webpage(f"{KENYALAW_BASE_URL}/search/?q=constitutional+rights&page=1", "search_page_structure.txt")
    
    # Inspect legislation page
    inspect_webpage(f"{KENYALAW_BASE_URL}/legislation/", "legislation_structure.txt")

if __name__ == "__main__":
    main()