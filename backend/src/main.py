from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
from starlette.responses import StreamingResponse
import asyncio

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

# Get Redis URL from Heroku
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_data = urlparse(redis_url)

# Update Redis configuration
REDIS_CONFIG = {
    'host': redis_data.hostname,
    'port': redis_data.port,
    'password': redis_data.password,
    'ssl': True if redis_url.startswith('rediss://') else False
}

# Initialize FastAPI app
app = FastAPI(
    title="Luzia Deep Research",
    description="AI-powered research assistant that generates comprehensive reports from web searches",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://luzia-research-frontend.herokuapp.com",
        "http://localhost:8501"  # For local development
    ],
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
    background_tasks: BackgroundTasks,
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
        
        async def generate():
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
            
            return formatted_output

        # Use asyncio.create_task to handle the long-running process
        result = await asyncio.create_task(generate())
        
        # Return response with appropriate content type
        return Response(
            content=result["content"],
            media_type=result["mime_type"],
            headers={
                "Content-Disposition": f"attachment; filename=research_report.{result['format']}"
            } if request.output_format in ["pdf", "docx"] else None
        )
        
    except Exception as e:
        logger.error("research_error", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("APP_ENV") == "development" else False
    )
