import os
from typing import List, Dict
from openai import AsyncOpenAI
import structlog
from config import Config

logger = structlog.get_logger()

class ResearchPlanner:
    def __init__(self, max_questions: int = 4):
        self.openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = "o3-mini"  # Using o3-mini model for reasoning
        self.max_questions = max_questions
        
    async def generate_research_plan(self, query: str) -> List[str]:
        """
        Generate a research plan based on the user query using O3-mini model.
        Returns a list of search queries that should be executed.
        """
        try:
            # Create the prompt for research plan generation
            prompt = self._create_research_plan_prompt(query)
            
            # Generate research plan using O3-mini
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                reasoning_effort="medium"  # Using medium reasoning as shown in example
            )
            
            # Extract and parse the research plan
            plan = response.choices[0].message.content
            search_queries = self._parse_research_plan(plan)
            
            # Limit to max_questions
            search_queries = search_queries[:self.max_questions]
            
            logger.info("research_plan_generated",
                       original_query=query,
                       num_search_queries=len(search_queries))
            
            return search_queries
            
        except Exception as e:
            logger.error("research_plan_generation_failed", error=str(e), query=query)
            raise
            
    def _create_research_plan_prompt(self, query: str) -> str:
        """
        Create a prompt for research plan generation.
        """
        return f"""You are a research planning assistant. Your task is to break down the following research query into specific, focused search queries.
The plan should have no more than {self.max_questions} search queries.

Research Query: {query}

Please provide your response in the following format:
# Research Plan
1. [First search query]
2. [Second search query]
3. [Third search query]
...

Make sure each search query is:
- Specific and focused
- Designed to gather factual information
- Written in a way that would yield relevant search results
- Related to a distinct aspect of the main research query
- Together, the queries should cover all important aspects of the research topic

Please provide the search queries only, without additional explanation."""
        
    def _parse_research_plan(self, plan: str) -> List[str]:
        """
        Parse the research plan response into a list of search queries.
        """
        # Split the plan into lines and filter out empty lines and headers
        lines = [line.strip() for line in plan.split('\n') if line.strip()]
        queries = []
        
        for line in lines:
            # Skip the header line if present
            if line.lower().startswith('# research plan'):
                continue
                
            # Remove numbering and brackets if present
            query = line.strip()
            if query[0].isdigit():
                query = query[query.find('.') + 1:].strip()
            query = query.strip('[]')
            
            if query:
                queries.append(query)
                
        return queries 