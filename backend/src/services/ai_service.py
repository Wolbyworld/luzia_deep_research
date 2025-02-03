import os
from typing import List, Dict, Optional, Tuple
from openai import AsyncOpenAI
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
import asyncio
from config import Config
from services.cache_service import CacheService

logger = structlog.get_logger()

class AIService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
        self.max_chunks = Config.MAX_CHUNKS_FOR_REPORT
        self.max_concurrent_requests = 10  # Increased concurrent requests since we're not batching
        self.cache_service = CacheService()
        
    async def generate_report(self, query: str, chunks: List[Dict[str, str]]) -> str:
        """
        Generate a research report based on the query and content chunks
        """
        try:
            # Log start of process
            logger.info("starting_research_generation", 
                       query=query, 
                       available_chunks=len(chunks))
            
            # Rerank chunks
            ranked_chunks = await self._rerank_chunks_with_embeddings(query, chunks)
            used_chunks = ranked_chunks[:self.max_chunks]
            
            logger.info("chunk_reranking_completed", 
                       total_chunks=len(chunks),
                       selected_chunks=len(used_chunks))
            
            # Build context and generate report
            context = self._build_context(used_chunks)
            prompt = self._create_report_prompt(query, context)
            
            # Log token usage before API call
            estimated_input_tokens = len(prompt) // 4  # Rough estimation
            
            logger.info("starting_gpt4_call", 
                       model=self.model,
                       estimated_input_tokens=estimated_input_tokens,
                       max_output_tokens=self.max_tokens)
            
            response = await self._generate_with_gpt4(prompt)
            
            # Log completion
            logger.info("research_metrics", 
                       chunks_available=len(chunks),
                       chunks_used=len(used_chunks),
                       embeddings_generated=len(chunks) + 1,  # chunks + query
                       estimated_input_tokens=estimated_input_tokens,
                       output_tokens=len(response) // 4,  # Rough estimation
                       model=self.model)
            
            return response
            
        except Exception as e:
            logger.error("report_generation_failed", error=str(e), query=query)
            raise
        
    async def generate_report_with_sources(self, query: str, chunks: List[Dict[str, str]]) -> Tuple[str, List[str]]:
        """
        Generate a research report and return both the report and its sources
        """
        try:
            # Log start of process
            logger.info("starting_research_generation", 
                       query=query, 
                       available_chunks=len(chunks))
            
            # Rerank chunks
            ranked_chunks = await self._rerank_chunks_with_embeddings(query, chunks)
            used_chunks = ranked_chunks[:self.max_chunks]
            
            logger.info("chunk_reranking_completed", 
                       total_chunks=len(chunks),
                       selected_chunks=len(used_chunks))
            
            # Extract sources from chunks
            sources = []
            for chunk in used_chunks:
                if 'url' in chunk and chunk['url'] not in sources:
                    sources.append(chunk['url'])
            
            # Build context and generate report
            context = self._build_context(used_chunks)
            prompt = self._create_report_prompt(query, context)
            
            # Log token usage before API call
            estimated_input_tokens = len(prompt) // 4  # Rough estimation
            
            logger.info("starting_gpt4_call", 
                       model=self.model,
                       estimated_input_tokens=estimated_input_tokens,
                       max_output_tokens=self.max_tokens)
            
            report = await self._generate_with_gpt4(prompt)
            
            # Log completion
            logger.info("research_metrics", 
                       chunks_available=len(chunks),
                       chunks_used=len(used_chunks),
                       embeddings_generated=len(chunks) + 1,  # chunks + query
                       estimated_input_tokens=estimated_input_tokens,
                       output_tokens=len(report) // 4,  # Rough estimation
                       model=self.model)
            
            return report, sources
            
        except Exception as e:
            logger.error("report_generation_failed", error=str(e), query=query)
            raise
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Get embedding for a single text
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=Config.EMBEDDING_MODEL,
                input=text
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            raise

    async def _get_all_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for all texts using pure parallel processing
        """
        # Create semaphore for controlling concurrent API calls
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        async def process_text(text: str, index: int):
            async with semaphore:
                embedding = await self._get_embedding(text)
                return index, embedding
        
        try:
            # Create tasks for all texts with their indices
            tasks = [process_text(text, i) for i, text in enumerate(texts)]
            
            # Process all texts concurrently
            results = await asyncio.gather(*tasks)
            
            # Sort by original index and return embeddings
            sorted_results = sorted(results, key=lambda x: x[0])
            return [embedding for _, embedding in sorted_results]
            
        except Exception as e:
            logger.error("parallel_embedding_failed", error=str(e))
            raise
        
    async def _rerank_chunks_with_embeddings(self, query: str, chunks: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Rerank chunks using OpenAI embeddings similarity with batch processing
        """
        try:
            # Prepare all texts for embedding (query + all chunks)
            chunk_texts = [chunk["content"] for chunk in chunks]
            all_texts = [query] + chunk_texts
            
            # Get embeddings for all texts in parallel batches
            all_embeddings = await self._get_all_embeddings(all_texts)
            
            # Separate query embedding and chunk embeddings
            query_embedding = all_embeddings[0]
            chunk_embeddings = all_embeddings[1:]
            
            # Calculate similarities
            similarities = [
                self._cosine_similarity(query_embedding, chunk_embedding)
                for chunk_embedding in chunk_embeddings
            ]
            
            # Sort chunks by similarity
            ranked_indices = np.argsort(similarities)[::-1]
            ranked_chunks = [chunks[i] for i in ranked_indices]
            
            return ranked_chunks
            
        except Exception as e:
            logger.error("chunk_reranking_failed", error=str(e), query=query)
            raise
        
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        """
        a = np.array(a)
        b = np.array(b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
    def _build_context(self, chunks: List[Dict[str, str]]) -> str:
        """
        Build context string from chunks while respecting token limits
        """
        context_parts = []
        total_tokens = 0
        system_prompt_tokens = 100  # Approximate tokens for system prompt
        max_available_tokens = Config.MAX_INPUT_TOKENS - system_prompt_tokens - 1000  # Buffer for query and other text
        
        for chunk in chunks:
            # Approximate token count (1 token ≈ 4 chars for English text)
            chunk_text = f"Source: {chunk['url']}\nTitle: {chunk['title']}\nContent: {chunk['content']}\n"
            chunk_tokens = len(chunk_text) // 4
            
            if total_tokens + chunk_tokens > max_available_tokens:
                break
            
            context_parts.append(chunk_text)
            total_tokens += chunk_tokens
        
        return "\n".join(context_parts)
        
    def _create_report_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for report generation with proper quotation format
        """
        return f"""Based on the following research query and source materials, generate a comprehensive report.
        
Query: {query}

Source Materials:
{context}

Please generate a detailed report that:
1. Synthesizes information from multiple sources
2. Uses proper quotation marks for direct quotes (e.g., "quoted text")
3. Maintains a neutral, academic tone
4. Organizes information logically
5. Highlights key findings and insights
6. Properly attributes information to sources using standard quotation format

For example:
According to [Source], "direct quote here." Another source states that "another quote here."

Report:"""
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_with_gpt4(self, prompt: str) -> str:
        """Generate text using GPT-4"""
        try:
            start_time = asyncio.get_event_loop().time()
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research assistant tasked with creating comprehensive reports based on provided content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            end_time = asyncio.get_event_loop().time()
            
            logger.info("gpt4_call_timing",
                       duration_seconds=round(end_time - start_time, 2),
                       prompt_tokens=response.usage.prompt_tokens,
                       completion_tokens=response.usage.completion_tokens,
                       total_tokens=response.usage.total_tokens)
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error("gpt4_generation_failed", error=str(e))
            raise
