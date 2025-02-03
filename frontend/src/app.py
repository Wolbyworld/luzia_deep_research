import streamlit as st
import httpx
import asyncio
import json
import base64
from typing import Optional
import os
from dotenv import load_dotenv
from pathlib import Path
import time

# Load environment variables from the root .env file
root_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(root_dir / "backend" / ".env")

# Initialize session state
if 'research_output' not in st.session_state:
    st.session_state.research_output = None
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None

# App configuration
if os.getenv("APP_ENV") == "production":
    API_URL = os.getenv("API_URL", "https://luzia-research-backend-ee9b4ecc575f.herokuapp.com")
else:
    API_URL = os.getenv("API_URL", "http://localhost:8000")

if API_URL.endswith('/'):
    API_URL = API_URL[:-1]

# Default configuration
DEFAULT_CONFIG = {
    "max_results": 10,
    "time_filter": "month",
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "min_chunk_length": 100,
    "max_chunks_for_report": 20,
    "temperature": 0.3,
    "max_tokens": 16000
}

# Update the PHASES with more detailed and engaging messages
PHASES = {
    "init": ("🚀 Initializing research process...", 0),
    "search": ("🔍 Searching the web for relevant sources...", 15),
    "extract": ("📚 Reading and extracting content from sources...", 30),
    "analyze": ("🧠 Analyzing and processing information...", 45),
    "rank": ("⭐ Ranking and selecting best content...", 60),
    "synthesize": ("🎯 Synthesizing information...", 75),
    "generate": ("✍️ Writing comprehensive report...", 90),
    "complete": ("✨ Report completed!", 100)
}

# Add engaging loading messages
LOADING_MESSAGES = {
    "search": [
        "Scanning academic papers...",
        "Exploring recent publications...",
        "Finding expert opinions...",
        "Discovering relevant sources...",
        "Analyzing search results..."
    ],
    "extract": [
        "Reading through articles...",
        "Extracting key information...",
        "Processing source materials...",
        "Gathering relevant data...",
        "Compiling research materials..."
    ],
    "analyze": [
        "Connecting the dots...",
        "Identifying patterns...",
        "Evaluating sources...",
        "Cross-referencing information...",
        "Processing complex data..."
    ],
    "generate": [
        "Crafting your report...",
        "Organizing findings...",
        "Adding citations...",
        "Polishing the content...",
        "Finalizing the research..."
    ]
}

class ProgressTracker:
    def __init__(self):
        self.progress_bar = None
        self.status_text = None
        self.detail_text = None
        self.metrics_container = None
        self.current_phase = None
        
    def init_progress(self):
        col1, col2 = st.columns([2, 1])
        with col1:
            self.progress_bar = st.progress(0)
            self.status_text = st.empty()
            self.detail_text = st.empty()
        with col2:
            self.metrics_container = st.empty()
        
    def show_progress(self, phase: str, metrics: dict = None):
        """Update progress bar with current phase and animated messages"""
        if not all([self.progress_bar, self.status_text, self.detail_text]):
            return
            
        self.current_phase = phase
        message, progress = PHASES.get(phase, ("Processing...", 50))
        self.progress_bar.progress(progress)
        self.status_text.markdown(f"### {message}")
        
        # Show animated sub-messages for the current phase
        if phase in LOADING_MESSAGES:
            messages = LOADING_MESSAGES[phase]
            current_msg = messages[int(time.time() * 0.5) % len(messages)]
            self.detail_text.markdown(f"*{current_msg}*")
        
        # Display metrics if available
        if metrics and self.metrics_container:
            metrics_md = "### 📊 Process Metrics\n"
            if "sources_found" in metrics:
                metrics_md += f"- Sources found: {metrics['sources_found']}\n"
            if "sources_processed" in metrics:
                metrics_md += f"- Sources processed: {metrics['sources_processed']}\n"
            if "chunks_total" in metrics:
                metrics_md += f"- Content chunks: {metrics['chunks_total']}\n"
            self.metrics_container.markdown(metrics_md)
    
    def clear(self):
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_text:
            self.status_text.empty()
        if self.detail_text:
            self.detail_text.empty()
        if self.metrics_container:
            self.metrics_container.empty()
        self.progress_bar = None
        self.status_text = None
        self.detail_text = None
        self.metrics_container = None

# Create a global progress tracker
progress_tracker = ProgressTracker()

async def check_research_status(job_id: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_URL}/api/research/{job_id}")
        return response.json() if response.status_code == 200 else None

async def generate_research(query: str, config: dict):
    """
    Generate research report and PDF
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Initialize with engaging UI
            progress_tracker.show_progress("init")
            await asyncio.sleep(1)  # Short pause for effect
            
            # Health check
            response = await client.get(f"{API_URL}/")
            if response.status_code != 200:
                st.error("API is not available")
                return None

            # Show search progress
            progress_tracker.show_progress("search")
            payload = {
                "query": query,
                "max_results": config["max_results"],
                "time_filter": config["time_filter"],
                "output_format": config.get("output_format", "markdown"),
                "title": f"Research Report: {query}"
            }
            
            # Extract and analyze
            progress_tracker.show_progress("extract")
            response = await client.post(
                f"{API_URL}/api/research",
                json=payload,
                timeout=120.0
            )
            
            # Show different phases while waiting
            for phase in ["analyze", "rank", "synthesize", "generate"]:
                await asyncio.sleep(2)  # Simulate progress
                progress_tracker.show_progress(phase)
            
            if response.status_code == 200:
                progress_tracker.show_progress("complete")
                await asyncio.sleep(1)  # Pause to show completion
                
            # Get the content directly from response
            if config.get("output_format") == "pdf":
                return {"content": response.content}
            else:
                content = response.text
                if not content:
                    st.error("Received empty response from server")
                    return None
                return {"content": content}
            
        except httpx.TimeoutException:
            st.error("Request timed out. The research is taking longer than expected.")
            return None
        except Exception as e:
            st.error(f"Error during research generation:\n{str(e)}")
            return None

def render_sidebar_config() -> dict:
    """Render sidebar configuration options"""
    st.sidebar.title("Settings")
    show_config = st.sidebar.toggle("Show Advanced Configuration")
    
    config = DEFAULT_CONFIG.copy()
    
    if show_config:
        st.sidebar.subheader("Advanced Configuration")
        
        # Search settings
        st.sidebar.markdown("#### Search Settings")
        config["max_results"] = st.sidebar.slider("Max Search Results", 1, 50, DEFAULT_CONFIG["max_results"])
        config["time_filter"] = st.sidebar.selectbox("Time Filter", ["day", "week", "month", "year"], 
                                                   index=["day", "week", "month", "year"].index(DEFAULT_CONFIG["time_filter"]))
        
        # Content Processing
        st.sidebar.markdown("#### Content Processing")
        config["chunk_size"] = st.sidebar.number_input("Chunk Size", 100, 2000, DEFAULT_CONFIG["chunk_size"])
        config["chunk_overlap"] = st.sidebar.number_input("Chunk Overlap", 0, 500, DEFAULT_CONFIG["chunk_overlap"])
        config["max_chunks_for_report"] = st.sidebar.number_input("Max Chunks for Report", 1, 50, DEFAULT_CONFIG["max_chunks_for_report"])
        
        # Model Settings
        st.sidebar.markdown("#### Model Settings")
        config["temperature"] = st.sidebar.slider("Temperature", 0.0, 1.0, DEFAULT_CONFIG["temperature"])
        config["max_tokens"] = st.sidebar.number_input("Max Output Tokens", 1000, 16384, DEFAULT_CONFIG["max_tokens"])
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
        💡 **Tips:**
        - Higher max results = more comprehensive but slower
        - Lower temperature = more focused results
        - Larger chunk size = better context but fewer chunks
        """)
    
    return config

# Function to load and display the logo
def display_logo():
    logo_path = root_dir / "assets" / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_contents = f.read()
            logo_b64 = base64.b64encode(logo_contents).decode()
            
        # Create a clickable logo that redirects to home with smaller size and styling
        st.markdown(
            f'<a href="/" target="_self"><img src="data:image/png;base64,{logo_b64}" style="max-width: 60px; margin: 10px 0;"></a>',
            unsafe_allow_html=True
        )

def main():
    st.set_page_config(
        page_title="Luzia Research",
        page_icon="🔍",
        layout="wide"
    )
    
    # Display the logo
    display_logo()
    
    st.title("Luzia Research Agent")
    st.markdown("""
    Generate comprehensive research reports from your questions using AI.
    Advanced settings are available in the sidebar for fine-tuning the research process.
    """)
    
    # Render sidebar configuration
    config = render_sidebar_config()

    # Main content with form
    with st.form(key="research_form"):
        query = st.text_area(
            "Enter your research question and press Enter:", 
            height=100,
            placeholder="Example: What are the latest developments in quantum computing?",
            key="query"
        )
        submit_button = st.form_submit_button("Generate Report", type="primary", use_container_width=True)
        
    # Handle form submission
    if submit_button:
        if not query:
            st.warning("Please enter a research question")
            return
            
        # Initialize progress tracking
        progress_tracker.init_progress()
        
        # Generate report
        result = asyncio.run(generate_research(query, config))
        
        if result and "content" in result:
            st.session_state.research_output = result["content"]
            progress_tracker.clear()
        else:
            st.error("Failed to generate report")
            progress_tracker.clear()
            return

    # Display report if available
    if st.session_state.research_output:
        st.markdown("## Research Report")
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["📄 Report", "🔍 Sources"])
        
        with tab1:
            st.markdown(st.session_state.research_output)
        
        with tab2:
            # Extract sources from markdown
            sources = [line.strip('* ') for line in st.session_state.research_output.split('\n') 
                      if line.startswith('*') and 'http' in line]
            if sources:
                st.markdown("### Referenced Sources")
                for source in sources:
                    st.markdown(f"- [{source}]({source})")
            else:
                st.info("No sources found in the report")
        
        # PDF download button - generate PDF only when requested
        if st.button("Generate PDF"):
            with st.spinner("Generating PDF..."):
                # Initialize progress tracking for PDF generation
                progress_tracker.init_progress()
                
                # Generate PDF version
                config["output_format"] = "pdf"
                config["title"] = f"Research Report: {query}"  # Add title for PDF
                
                # Use the same job queue system for PDF generation
                pdf_content = asyncio.run(generate_research(query, config))
                
                progress_tracker.clear()
                
                if pdf_content and "content" in pdf_content:
                    st.session_state.pdf_data = pdf_content["content"]
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_content["content"],
                        file_name=f"research_report_{query[:30]}.pdf".replace(" ", "_"),
                        mime="application/pdf",
                        help="Download the report as a PDF file"
                    )
                else:
                    st.error("Failed to generate PDF")

if __name__ == "__main__":
    main() 