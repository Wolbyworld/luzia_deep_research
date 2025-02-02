import os
from typing import List, Dict, Optional
from openai import AsyncOpenAI
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
import asyncio
from ..config import Config

logger = structlog.get_logger()

class AIService:
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.model = Config.OPENAI_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
        self.max_chunks = Config.MAX_CHUNKS_FOR_REPORT
        self.batch_size = 20  # Maximum batch size for embeddings
        
    async def generate_report(self, query: str, chunks: List[Dict[str, str]]) -> str:
        """
        Generate a research report based on the query and content chunks
        """
        try:
            # Generate new report
            ranked_chunks = await self._rerank_chunks_with_embeddings(query, chunks)
            context = self._build_context(ranked_chunks[:self.max_chunks])
            prompt = self._create_report_prompt(query, context)
            response = await self._generate_with_gpt4(prompt)
            
            return response
            
        except Exception as e:
            logger.error("report_generation_failed", error=str(e), query=query)
            raise
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for a batch of texts
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=Config.EMBEDDING_MODEL,
                input=texts
            )
            return [embedding.embedding for embedding in response.data]
            
        except Exception as e:
            logger.error("batch_embedding_generation_failed", error=str(e), batch_size=len(texts))
            raise

    async def _get_all_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for all texts using batching and parallel processing
        """
        # Split texts into batches
        batches = [texts[i:i + self.batch_size] for i in range(0, len(texts), self.batch_size)]
        
        # Process batches in parallel
        try:
            embedding_batches = await asyncio.gather(
                *[self._get_embeddings_batch(batch) for batch in batches]
            )
            
            # Flatten the results
            return [embedding for batch in embedding_batches for embedding in batch]
            
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
        Build context string from chunks
        """
        context_parts = []
        for chunk in chunks:
            context_parts.append(f"Source: {chunk['url']}\nTitle: {chunk['title']}\nContent: {chunk['content']}\n")
        return "\n".join(context_parts)
        
    def _create_report_prompt(self, query: str, context: str) -> str:
        """
        Create prompt for report generation
        """
        return f"""Based on the following research query and source materials, generate a comprehensive report.
        
Query: {query}

Source Materials:
{context}

Please generate a detailed report that:
1. Synthesizes information from multiple sources
2. Provides accurate citations
3. Maintains a neutral, academic tone
4. Organizes information logically
5. Highlights key findings and insights

Report:"""
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _generate_with_gpt4(self, prompt: str) -> str:
        """
        Generate text using OpenAI GPT-4 with retry logic
        """
        try:
            completion = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a research assistant that generates comprehensive reports based on provided sources."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return completion.choices[0].message.content
            
        except Exception as e:
            logger.error("gpt4_generation_failed", error=str(e))
            raise
