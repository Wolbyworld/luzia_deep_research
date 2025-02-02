from typing import List, Optional, Dict
import httpx
import os
from datetime import datetime, timedelta

class SearchResult:
    def __init__(self, title: str, link: str, snippet: str):
        self.title = title
        self.link = link
        self.snippet = snippet

class WebSearcher:
    def __init__(self):
        self.serper_api_key = os.getenv("SERPER_API_KEY")
        self.azure_api_key = os.getenv("AZURE_SEARCH_KEY")
        self.max_results = int(os.getenv("MAX_SEARCH_RESULTS", "10"))
        
    async def search(self, query: str, time_filter: Optional[str] = None) -> List[SearchResult]:
        """
        Perform web search using available search provider
        """
        if self.serper_api_key:
            return await self._search_with_serper(query, time_filter)
        elif self.azure_api_key:
            return await self._search_with_azure(query, time_filter)
        else:
            raise ValueError("No search API key configured")

    async def _search_with_serper(self, query: str, time_filter: Optional[str]) -> List[SearchResult]:
        """
        Search using Serper.dev (Google Search API)
        """
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": self.serper_api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "num": self.max_results
        }
        
        if time_filter:
            payload["timeRange"] = time_filter
            
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("organic", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", "")
                ))
            
            return results

    async def _search_with_azure(self, query: str, time_filter: Optional[str]) -> List[SearchResult]:
        """
        Search using Azure Bing Search API
        """
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            "Ocp-Apim-Subscription-Key": self.azure_api_key
        }
        
        params = {
            "q": query,
            "count": self.max_results,
            "responseFilter": "Webpages"
        }
        
        if time_filter:
            # Convert time filter to Azure format
            time_mappings = {
                "day": "Day",
                "week": "Week",
                "month": "Month",
                "year": "Year"
            }
            params["freshness"] = time_mappings.get(time_filter.lower(), "Month")
            
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("webPages", {}).get("value", []):
                results.append(SearchResult(
                    title=item.get("name", ""),
                    link=item.get("url", ""),
                    snippet=item.get("snippet", "")
                ))
            
            return results
