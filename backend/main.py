from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv

from src.core.searcher import WebSearcher
from src.core.content_extractor import ContentExtractor
from src.utils.chunking import ContentProcessor
from src.services.ai_service import AIService
from src.services.formatter_service import FormatterService
from src.utils.logger import setup_logging
from src.config import Config, OutputFormat

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
    output_format: OutputFormat = Field(Config.DEFAULT_OUTPUT_FORMAT, description="Output format (text, markdown, pdf, docx)")
    title: Optional[str] = Field(None, description="Optional title for the report")

# Service dependencies
def get_searcher():
    return WebSearcher()

def get_content_extractor():
    return ContentExtractor()

def get_content_processor():
    return ContentProcessor()

def get_ai_service():
    return AIService()

def get_formatter_service():
    return FormatterService()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Luzia Deep Research API"}

@app.post("/api/research")
async def generate_research(
    request: SearchRequest,
    searcher: WebSearcher = Depends(get_searcher),
    extractor: ContentExtractor = Depends(get_content_extractor),
    processor: ContentProcessor = Depends(get_content_processor),
    ai_service: AIService = Depends(get_ai_service),
    formatter: FormatterService = Depends(get_formatter_service)
):
    """
    Generate a research report based on the query
    """
    try:
        # Log request
        logger.info("research_request_received", 
                   query=request.query, 
                   max_results=request.max_results,
                   output_format=request.output_format)
        
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
        
        # 5. Get unique sources
        sources = list(set(content["url"] for content in contents))
        
        # 6. Format output
        formatted_output = formatter.format_output(
            content=report,
            sources=sources,
            output_format=request.output_format,
            title=request.title
        )
        
        logger.info("research_completed", 
                   query=request.query, 
                   sources_count=len(sources),
                   format=request.output_format)
        
        # Return response with appropriate content type
        return Response(
            content=formatted_output["content"],
            media_type=formatted_output["mime_type"],
            headers={
                "Content-Disposition": f"attachment; filename=research_report.{formatted_output['format']}"
            } if request.output_format in ["pdf", "docx"] else None
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
