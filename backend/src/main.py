from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from dotenv import load_dotenv
import json
import asyncio

from core.searcher import WebSearcher
from core.content_extractor import ContentExtractor
from utils.chunking import ContentProcessor
from services.ai_service import AIService
from services.formatter_service import FormatterService
from services.pro_research_service import ProResearchService
from utils.logger import setup_logging
from config import Config, OutputFormat

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
    max_results: Optional[int] = Field(10, ge=1, le=50, description="Number of search results to process")
    time_filter: Optional[str] = Field(None, description="Time filter for search results (day, week, month, year)")
    output_format: OutputFormat = Field(Config.DEFAULT_OUTPUT_FORMAT, description="Output format (text, markdown, pdf, docx)")
    title: Optional[str] = Field(None, description="Optional title for the report")
    is_pro_mode: Optional[bool] = Field(False, description="Whether to use pro mode with research planning")
    max_questions: Optional[int] = Field(4, ge=2, le=8, description="Maximum number of research questions in pro mode")

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

def get_pro_research_service():
    return ProResearchService()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Luzia Deep Research API"}

async def process_content(
    query: str,
    max_results: int,
    time_filter: Optional[str],
    searcher: WebSearcher,
    extractor: ContentExtractor,
    processor: ContentProcessor
) -> List[dict]:
    """Helper function to process content for a query"""
    # 1. Perform web search
    search_results = await searcher.search(query, time_filter)
    if not search_results:
        raise HTTPException(status_code=404, detail="No search results found")
    
    # 2. Extract content from URLs
    contents = []
    successful_extractions = 0
    failed_extractions = 0
    for result in search_results[:max_results]:
        try:
            content = await extractor.extract_from_url(result.link)
            if content.get("content"):
                contents.append(content)
                successful_extractions += 1
            else:
                failed_extractions += 1
        except:
            failed_extractions += 1
    
    if not contents:
        raise HTTPException(status_code=404, detail="Could not extract content from search results")
    
    # 3. Process and chunk content
    processed_contents = processor.process_contents(contents)
    
    return processed_contents

@app.post("/api/research")
async def generate_research(
    request: SearchRequest,
    searcher: WebSearcher = Depends(get_searcher),
    extractor: ContentExtractor = Depends(get_content_extractor),
    processor: ContentProcessor = Depends(get_content_processor),
    ai_service: AIService = Depends(get_ai_service),
    pro_service: ProResearchService = Depends(get_pro_research_service),
    formatter: FormatterService = Depends(get_formatter_service)
):
    """
    Generate a research report based on the query
    """
    metrics = {
        "sources_found": 0,
        "sources_processed": 0,
        "chunks_total": 0,
        "total_tokens": 0
    }
    
    try:
        # Log initial request
        logger.info("research_request_received", 
                   query=request.query, 
                   max_results=request.max_results,
                   output_format=request.output_format,
                   is_pro_mode=request.is_pro_mode)
        
        if request.is_pro_mode:
            # Pro mode: Use research planning
            pro_service.max_questions = request.max_questions
            
            # Define progress callback
            async def progress_callback(phase: str, progress: int):
                logger.info("pro_research_progress", phase=phase, progress=progress)
            
            # Generate comprehensive report with research planning
            result = await pro_service.generate_comprehensive_report(
                request.query,
                progress_callback=progress_callback
            )
            
            # Format the final report
            formatted_output = formatter.format_output(
                content=result["final_report"],
                sources=[],  # Sources will be in the report content
                output_format=request.output_format,
                title=request.title
            )
            
            if request.output_format in ["pdf", "docx"]:
                return Response(
                    content=formatted_output["content"],
                    media_type=formatted_output["mime_type"],
                    headers={
                        "Content-Disposition": f"attachment; filename=research_report.{formatted_output['format']}"
                    }
                )
            else:
                return {
                    "final_report": result["final_report"],
                    "sub_reports": result["sub_reports"],
                    "research_plan": result["research_plan"]
                }
        
        else:
            # Standard mode: Process content and generate single report
            processed_contents = await process_content(
                request.query,
                request.max_results,
                request.time_filter,
                searcher,
                extractor,
                processor
            )
            
            # Generate report
            report = await ai_service.generate_report(request.query, processed_contents)
            
            # Format output
            formatted_output = formatter.format_output(
                content=report,
                sources=[],  # Sources will be in the report content
                output_format=request.output_format,
                title=request.title
            )
            
            return Response(
                content=formatted_output["content"],
                media_type=formatted_output["mime_type"],
                headers={
                    "Content-Disposition": f"attachment; filename=research_report.{formatted_output['format']}"
                } if request.output_format in ["pdf", "docx"] else None
            )
        
    except Exception as e:
        logger.error("research_error", error=str(e), query=request.query, metrics=metrics)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "metrics": metrics
            }
        )

@app.post("/api/research/stream")
async def generate_research_stream(
    request: SearchRequest,
    searcher: WebSearcher = Depends(get_searcher),
    extractor: ContentExtractor = Depends(get_content_extractor),
    processor: ContentProcessor = Depends(get_content_processor),
    ai_service: AIService = Depends(get_ai_service),
    pro_service: ProResearchService = Depends(get_pro_research_service),
    formatter: FormatterService = Depends(get_formatter_service)
):
    """
    Generate a research report with streaming progress updates
    """
    async def event_generator():
        try:
            if request.is_pro_mode:
                # Pro mode: Use research planning
                pro_service.max_questions = request.max_questions
                
                # Create a queue for progress updates
                progress_queue = asyncio.Queue()
                
                async def progress_callback(phase: str, progress: int):
                    await progress_queue.put((phase, progress))
                
                # Start the research task
                research_task = asyncio.create_task(
                    pro_service.generate_comprehensive_report(
                        request.query,
                        progress_callback=progress_callback
                    )
                )
                
                # Keep sending progress updates until research is complete
                while not research_task.done():
                    try:
                        # Wait for progress update with timeout
                        phase, progress = await asyncio.wait_for(
                            progress_queue.get(),
                            timeout=1.0
                        )
                        data = {
                            "progress": progress,
                            "phase": phase
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error("progress_update_failed", error=str(e))
                        continue
                
                # Get the final result
                try:
                    result = await research_task
                    yield f"data: {json.dumps({'result': result})}\n\n"
                except Exception as e:
                    logger.error("research_task_failed", error=str(e))
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            else:
                # Standard mode: Process content and generate single report
                processed_contents = await process_content(
                    request.query,
                    request.max_results,
                    request.time_filter,
                    searcher,
                    extractor,
                    processor
                )
                
                # Generate report
                report = await ai_service.generate_report(request.query, processed_contents)
                
                # Send final result
                yield f"data: {json.dumps({'result': {'final_report': report}})}\n\n"
                
        except Exception as e:
            logger.error("streaming_research_failed", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("APP_ENV") == "development" else False
    )
