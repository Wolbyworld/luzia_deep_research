# Luzia Deep Research

An AI-powered research assistant that generates comprehensive reports from web searches. Built with FastAPI, OpenAI, and modern Python async capabilities.

## Features

- 🔍 Web search with time filtering (using Serper.dev or Azure)
- 📄 Smart content extraction from web pages
- 🤖 Advanced text processing with OpenAI GPT-4
- 🎯 Semantic search using OpenAI embeddings
- 📊 Intelligent content chunking and reranking
- 🚀 Async processing for better performance

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key
- Serper.dev API key or Azure Search key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/Wolbyworld/luzia_deep_research.git
cd luzia_deep_research
```

2. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your API keys and configuration.

### Running the Service

1. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

2. Test the service:
```bash
python test_api.py
```

Or use the interactive API docs at `http://localhost:8000/docs`

## Configuration

Key environment variables:

```env
# Search API (Choose one)
SERPER_API_KEY=your_serper_api_key
AZURE_SEARCH_KEY=your_azure_search_key

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=chatgpt-4o-latest

# App Settings
MAX_SEARCH_RESULTS=10
MAX_TOKENS=4000
TEMPERATURE=0.3
```

## Project Structure

```
backend/
├── src/
│   ├── core/           # Core business logic
│   │   ├── searcher.py     # Web search functionality
│   │   └── content_extractor.py
│   ├── services/      # External service integrations
│   │   └── ai_service.py   # OpenAI integration
│   └── utils/         # Utility functions
│       └── chunking.py     # Content processing
├── tests/            # Test files
├── main.py          # FastAPI application
└── requirements.txt
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
