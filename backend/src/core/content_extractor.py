from bs4 import BeautifulSoup
import httpx
from typing import Optional, Dict
import re
from urllib.parse import urlparse

class ContentExtractor:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
    async def extract_from_url(self, url: str) -> Dict[str, str]:
        """
        Extract content from a given URL
        """
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                return self._parse_content(response.text, url)
        except Exception as e:
            return {
                "title": "",
                "content": "",
                "error": str(e)
            }

    def _parse_content(self, html: str, url: str) -> Dict[str, str]:
        """
        Parse HTML content and extract relevant information
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe']):
            element.decompose()
            
        # Get title
        title = self._extract_title(soup)
        
        # Get main content
        content = self._extract_main_content(soup)
        
        return {
            "title": title,
            "content": content,
            "url": url
        }
        
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """
        Extract the title of the page
        """
        # Try different title elements
        title = ""
        if soup.find("meta", property="og:title"):
            title = soup.find("meta", property="og:title")["content"]
        elif soup.title:
            title = soup.title.string
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)
            
        return self._clean_text(title)
        
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract the main content from the page
        """
        # Try to find main content container
        main_content = ""
        
        # Look for common content containers
        content_tags = [
            soup.find("main"),
            soup.find("article"),
            soup.find(id=re.compile("^(content|main|article)")),
            soup.find(class_=re.compile("^(content|main|article)"))
        ]
        
        for tag in content_tags:
            if tag:
                main_content = tag.get_text(separator=' ', strip=True)
                if len(main_content) > 100:  # Minimum content length
                    break
                    
        # If no main content found, fall back to body text
        if not main_content:
            main_content = soup.body.get_text(separator=' ', strip=True) if soup.body else ""
            
        return self._clean_text(main_content)
        
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text
        """
        if not text:
            return ""
            
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        # Remove multiple punctuation
        text = re.sub(r'([.,!?])\1+', r'\1', text)
        
        return text.strip()
