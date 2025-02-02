# Luzia Deep Research Backend

## System Architecture and Flow

```
[User Input/Query]
       │
       v
[API Request] ───────────────────────┐
       │                             │
       v                             v
[FastAPI Backend] ────────► [Search Results Retrieval]
       │                    * Bing Search API
       │                    * Configurable time filters
       │                    * Rate limiting
       │
       v
[Content Extraction] ◄────── [URL Processing]
* HTML parsing                * Async fetching
* Text cleaning               * Error handling
* Metadata extraction         * Rate limiting
       │
       v
[Content Processing]
* Text chunking
* Token management
* Context window optimization
       │
       v
[Semantic Processing]
* Embeddings generation
* Chunk ranking
* Relevance scoring
       │
       v
[Report Generation]
* Context assembly
* Prompt engineering
* AI model interaction
       │
       v
[Final Response]
```

## Configurable Parameters

### 1. Request Configuration
- `base_url`: Server endpoint (default: "http://localhost:8000")
- `timeout`: Request timeout in seconds (default: 120.0)
  * Adjust based on content processing needs
  * Consider increasing for larger result sets

### 2. Search Parameters
- `max_results`: Number of search results to process (default: 5)
  * Range: 1-20
  * Affects processing time and API costs
  * More results = better coverage but slower processing

- `time_filter`: Time range for search results
  * Options: "day", "week", "month", "year"
  * Affects result relevance and freshness
  * Shorter ranges process faster

### 3. Content Processing
- `chunk_size`: Size of text chunks for processing
  * Configured in ContentProcessor
  * Affects context quality and token usage
  * Default: 1000 characters

- `overlap`: Overlap between chunks
  * Prevents context loss at chunk boundaries
  * Default: 100 characters

### 4. Environment Variables (.env)
- `OPENAI_MODEL`: AI model for report generation
  * Options: gpt-4-turbo-preview, gpt-4, etc.
  * Affects quality and speed
  * Impacts API costs

- `MAX_TOKENS`: Maximum tokens for report generation
  * Affects response length and detail
  * Consider model context window limits
  * Default: 4000

- `TEMPERATURE`: AI response creativity (0.0-1.0)
  * Lower = more focused/deterministic
  * Higher = more creative/varied
  * Default: 0.3

- `EMBEDDING_MODEL`: Model for semantic processing
  * Default: text-embedding-ada-002
  * Used for chunk ranking and relevance

## Performance Optimization Guide

### 1. Speed Optimization
- Decrease `max_results` (3-5 for faster results)
- Use shorter `time_filter` ("day" or "week")
- Reduce `chunk_size` and `overlap`
- Adjust `timeout` based on typical response times
- Use faster AI models (e.g., GPT-3.5-turbo)

### 2. Quality Optimization
- Increase `max_results` (10-20 for comprehensive research)
- Use longer `time_filter` for broader coverage
- Increase `chunk_size` for better context
- Adjust `TEMPERATURE` (0.1-0.3 for focused results)
- Increase `MAX_TOKENS` for detailed reports
- Use more capable AI models (e.g., GPT-4)

### 3. Cost Optimization
- Balance `max_results` with API usage
- Optimize `chunk_size` to minimize embedding API calls
- Choose appropriate model tiers
- Implement caching for frequent queries
- Use efficient rate limiting

### 4. Balanced Settings (Recommended)
- `max_results`: 5
- `time_filter`: "month"
- `chunk_size`: 1000
- `overlap`: 100
- `timeout`: 120.0
- `TEMPERATURE`: 0.3
- `MAX_TOKENS`: 4000

## Rate Limiting and API Considerations

### Search API
- Default: 5 requests per minute
- Configurable in environment settings
- Consider service tier limits

### Content Extraction
- Default: 20 requests per minute
- Parallel processing with rate limiting
- Respects robots.txt

### AI API
- Managed by provider limits
- Token usage monitoring
- Cost management features

## Error Handling and Resilience

- Automatic retries for transient failures
- Graceful degradation for unavailable services
- Comprehensive error reporting
- Request timeout management
- Invalid URL handling
- Rate limit compliance 