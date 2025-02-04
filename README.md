# Luzia Deep Research

An AI-powered research assistant that generates comprehensive reports from web searches. Built with FastAPI, OpenAI, and modern Python async capabilities, featuring a Streamlit frontend for easy interaction.

## Features

- 🔍 Web search with time filtering (using Serper.dev or Azure)
- 📄 Smart content extraction from web pages
- 🤖 Advanced text processing with OpenAI GPT-4
- 🎯 Semantic search using OpenAI embeddings
- 📊 Intelligent content chunking and reranking
- 🚀 Async processing for better performance
- 💾 Redis caching for improved response times
- 🖥️ User-friendly Streamlit interface

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Serper.dev API key or Azure Search key
- Redis (optional, for caching)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Wolbyworld/luzia_deep_research.git
cd luzia_deep_research
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd ../frontend
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cd ../backend
cp .env.example .env
```

Edit `.env` with your API keys and configuration.

### Running the Service

1. Start the Redis server (optional):
```bash
redis-server
```

2. Start the FastAPI backend:
```bash
cd backend
uvicorn main:app --reload
```

3. Start the Streamlit frontend:
```bash
cd frontend/src
streamlit run streamlit_app.py
```

The frontend will be available at `http://localhost:8501`
The API documentation is available at `http://localhost:8000/docs`

## Configuration

### Quality-Affecting Parameters

These environment variables significantly impact the quality of the research output:

```env
# Search Configuration
MAX_SEARCH_RESULTS=10          # Number of sources to process (higher = more comprehensive)

# OpenAI Model Settings
OPENAI_MODEL=chatgpt-4o-latest # Latest GPT-4 model for best quality
EMBEDDING_MODEL=text-embedding-ada-002  # For semantic search
MAX_TOKENS=4000                # Maximum response length
TEMPERATURE=0.3               # Lower = more focused and consistent output

# Caching
CACHE_TTL=86400               # Cache lifetime in seconds (24 hours)
```

### Other Configuration Options

```env
# Search API (Choose one)
SERPER_API_KEY=your_serper_api_key
AZURE_SEARCH_KEY=your_azure_search_key

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# App Settings
APP_ENV=development
LOG_LEVEL=INFO
```

## Project Structure

```
luzia_deep_research/
├── frontend/                # Streamlit frontend
│   ├── src/
│   │   └── streamlit_app.py  # Main frontend application
│   └── requirements.txt
│
├── backend/                 # FastAPI backend
│   ├── src/
│   │   ├── core/           # Core business logic
│   │   │   ├── searcher.py     # Web search functionality
│   │   │   └── content_extractor.py
│   │   ├── services/      # External service integrations
│   │   │   └── ai_service.py   # OpenAI integration
│   │   └── utils/         # Utility functions
│   │       └── chunking.py     # Content processing
│   ├── tests/            # Test files
│   ├── main.py          # FastAPI application
│   └── requirements.txt
│
├── assets/              # Project assets and documentation
└── heroku.yml          # Heroku deployment configuration
```

## API Endpoints

- `GET /` - Health check
- `POST /api/research` - Generate research report
  - Parameters:
    - `query`: Research question
    - `max_results`: Number of sources to process (default: 10)
    - `time_filter`: Time range for search (day/week/month/year)

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)
