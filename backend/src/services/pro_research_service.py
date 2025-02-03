import os
from typing import List, Dict, Tuple
from openai import AsyncOpenAI
import structlog
from config import Config
from services.research_planner import ResearchPlanner
from services.ai_service import AIService
from datetime import datetime
import asyncio

logger = structlog.get_logger()

class ProResearchService:
    def __init__(self, max_questions: int = 4):
        self.openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.planner = ResearchPlanner(max_questions=max_questions)
        self.ai_service = AIService()
        self.max_concurrent_requests = 3  # Limit concurrent API calls
        
    def _get_current_date(self) -> str:
        """Get current date in a readable format"""
        return datetime.now().strftime("%B %Y")
        
    async def generate_comprehensive_report(self, query: str, progress_callback=None) -> Dict:
        """
        Generate a comprehensive research report using the pro-mode flow:
        1. Generate research plan
        2. Execute each research query in parallel
        3. Compile final report
        """
        try:
            current_date = self._get_current_date()
            
            # Step 1: Generate research plan
            if progress_callback:
                await progress_callback("Generating research plan...", 0)
                
            search_queries = await self.planner.generate_research_plan(f"{query} (as of {current_date})")
            
            if progress_callback:
                await progress_callback(f"Research plan generated with {len(search_queries)} queries", 10)
            
            # Step 2: Generate reports for each query in parallel
            total_queries = len(search_queries)
            active_queries = set()  # Track active queries
            
            # Create a semaphore to limit concurrent API calls
            semaphore = asyncio.Semaphore(self.max_concurrent_requests)
            
            async def process_query(i: int, search_query: str):
                async with semaphore:
                    if progress_callback:
                        progress = 10 + (i + 1) * 70 // total_queries
                        active_queries.add(i)  # Add query to active set
                        # Show all active queries in the progress message
                        active_msg = "\n".join([f"🔍 Query {j+1}/{total_queries}: {search_queries[j]}" 
                                              for j in sorted(active_queries)])
                        await progress_callback(f"Researching multiple queries:\n{active_msg}", progress)
                    
                    try:
                        report = await self.ai_service.generate_report(search_query, [])
                        return {
                            "query": search_query,
                            "content": report
                        }
                    finally:
                        if progress_callback:
                            active_queries.remove(i)  # Remove query from active set
            
            # Create tasks for all queries
            tasks = [process_query(i, query) for i, query in enumerate(search_queries)]
            
            # Execute all tasks in parallel
            sub_reports = await asyncio.gather(*tasks)
            
            if progress_callback:
                await progress_callback("Compiling final report...", 80)
            
            # Step 3: Compile final report
            final_report = await self._compile_final_report(query, sub_reports, current_date)
            
            if progress_callback:
                await progress_callback("Research complete!", 100)
            
            return {
                "final_report": final_report,
                "sub_reports": sub_reports,
                "research_plan": search_queries
            }
            
        except Exception as e:
            logger.error("comprehensive_research_failed", error=str(e), query=query)
            raise
            
    async def _compile_final_report(self, main_query: str, sub_reports: List[Dict], current_date: str) -> str:
        """
        Compile a final report from all sub-reports, handling token limits.
        """
        try:
            # First try to compile with full reports
            full_content = self._prepare_compilation_content(main_query, sub_reports, current_date)
            
            try:
                return await self._generate_compilation(full_content)
            except Exception as e:
                if "maximum context length" in str(e).lower():
                    # If we hit token limit, try with summarized reports in parallel
                    logger.info("compilation_token_limit_exceeded", 
                              message="Retrying with summarized reports")
                    
                    summarized_reports = await self._summarize_reports(sub_reports)
                    summarized_content = self._prepare_compilation_content(main_query, summarized_reports, current_date)
                    return await self._generate_compilation(summarized_content)
                else:
                    raise
                    
        except Exception as e:
            logger.error("report_compilation_failed", error=str(e))
            raise
            
    def _prepare_compilation_content(self, main_query: str, reports: List[Dict], current_date: str) -> str:
        """
        Prepare the content for final compilation with optimized prompt.
        """
        # Prepare a concise version of each report
        sections = []
        for i, report in enumerate(reports, 1):
            # Extract key points from the report content (first few sentences)
            content = report['content'].split('.')[:3]  # Take first 3 sentences
            content = '. '.join(content) + '.'
            sections.append(f"Query {i}: {report['query']}\nKey Findings: {content}\n")
            
        all_findings = "\n".join(sections)
        
        return f"""As an expert research analyst, synthesize these findings into a comprehensive report.

Main Query: {main_query}
Date: {current_date}

Research Findings:
{all_findings}

Create a concise yet comprehensive report that:
1. Directly answers the main query
2. Synthesizes key insights from all research
3. Maintains academic tone
4. References specific findings (as Query X)
5. Notes current as of {current_date}

Report:"""
        
    async def _generate_compilation(self, content: str) -> str:
        """
        Generate the final compilation using the AI model with optimized parameters.
        """
        try:
            completion = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a research analyst synthesizing findings into clear, concise reports."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0.3  # Lower temperature for more focused output
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error("compilation_generation_failed", error=str(e))
            raise
        
    async def _summarize_reports(self, reports: List[Dict]) -> List[Dict]:
        """
        Create summarized versions of each report in parallel
        """
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def summarize_report(report: Dict) -> Dict:
            async with semaphore:
                try:
                    summary_prompt = f"""Summarize the following research findings in a concise way while preserving key information:

{report['content']}

Summary:"""
                    
                    completion = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "user",
                                "content": summary_prompt
                            }
                        ],
                        max_tokens=1000
                    )
                    
                    return {
                        "query": report["query"],
                        "content": completion.choices[0].message.content.strip()
                    }
                except Exception as e:
                    logger.error("report_summarization_failed", error=str(e))
                    raise
        
        # Create tasks for all reports
        tasks = [summarize_report(report) for report in reports]
        
        # Execute all tasks in parallel
        return await asyncio.gather(*tasks) 