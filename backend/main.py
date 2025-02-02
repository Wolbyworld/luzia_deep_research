from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv

from src.core.searcher import WebSearcher
from src.core.content_extractor import ContentExtractor
from src.utils.chunking import ContentProcessor
from src.services.ai_service import AIService
from src.utils.logger import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging()

# Initialize FastAPI app
app = FastAPI(
    title="Luzia Deep Research",
    description="AI-powered research assistant that generates comprehensive reports from web searches",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="The research query to search for")
    max_results: Optional[int] = Field(10, ge=1, le=20, description="Number of search results to process")
    time_filter: Optional[str] = Field(None, description="Time filter for search results (day, week, month, year)")

class ResearchResponse(BaseModel):
    content: str = Field(..., description="The generated research report")
    sources: List[str] = Field(..., description="List of sources used in the report")

# Service dependencies
def get_searcher():
    return WebSearcher()

def get_content_extractor():
    return ContentExtractor()

def get_content_processor():
    return ContentProcessor()

def get_ai_service():
    return AIService()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Luzia Deep Research API"}

@app.post("/api/research", response_model=ResearchResponse)
async def generate_research(
    request: SearchRequest,
    searcher: WebSearcher = Depends(get_searcher),
    extractor: ContentExtractor = Depends(get_content_extractor),
    processor: ContentProcessor = Depends(get_content_processor),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Generate a research report based on the query
    """
    try:
        # Log request
        logger.info("research_request_received", query=request.query, max_results=request.max_results)
        
        # 1. Perform web search
        search_results = await searcher.search(request.query, request.time_filter)
        if not search_results:
            raise HTTPException(status_code=404, detail="No search results found")
            
        logger.info("search_completed", results_count=len(search_results))
        
        # 2. Extract content from URLs
        contents = []
        for result in search_results[:request.max_results]:
            content = await extractor.extract_from_url(result.link)
            if content.get("content"):  # Only include if content was successfully extracted
                contents.append(content)
                
        if not contents:
            raise HTTPException(status_code=404, detail="Could not extract content from search results")
            
        logger.info("content_extraction_completed", extracted_count=len(contents))
        
        # 3. Process and chunk content
        processed_contents = processor.process_contents(contents)
        logger.info("content_processing_completed", chunks_count=len(processed_contents))
        
        # 4. Generate report
        report = await ai_service.generate_report(request.query, processed_contents)
        
        # 5. Prepare response
        sources = list(set(content["url"] for content in contents))
        
        logger.info("research_completed", query=request.query, sources_count=len(sources))
        
        return ResearchResponse(
            content=report,
            sources=sources
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("research_error", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail="An error occurred while generating the research report")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("APP_ENV") == "development" else False
    )
