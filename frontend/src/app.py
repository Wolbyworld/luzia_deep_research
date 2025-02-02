import streamlit as st
import httpx
import asyncio
import json
import base64
from typing import Optional
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from the root .env file
root_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(root_dir / "backend" / ".env")

# Initialize session state
if 'research_output' not in st.session_state:
    st.session_state.research_output = None
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None

# App configuration
API_URL = os.getenv("API_URL", "https://luzia-research-backend-ee9b4ecc575f.herokuapp.com")
if API_URL.endswith('/'):
    API_URL = API_URL[:-1]

# Default configuration
DEFAULT_CONFIG = {
    "max_results": 5,
    "time_filter": "month",
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "min_chunk_length": 100,
    "max_chunks_for_report": 10,
    "temperature": 0.3,
    "max_tokens": 4000
}

# Progress phases
PHASES = {
    "init": ("Initializing...", 0),
    "search": ("Searching for relevant content...", 20),
    "extract": ("Extracting content from sources...", 40),
    "process": ("Processing and analyzing content...", 60),
    "generate": ("Generating final report...", 80),
    "complete": ("Report completed!", 100)
}

class ProgressTracker:
    def __init__(self):
        self.progress_bar = None
        self.status_text = None
    
    def init_progress(self):
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
    
    def show_progress(self, phase: str):
        """Update progress bar with current phase"""
        if self.progress_bar is not None and self.status_text is not None:
            message, progress = PHASES.get(phase, ("Processing...", 50))
            self.progress_bar.progress(progress)
            self.status_text.text(f"Phase: {message}")
    
    def clear(self):
        if self.progress_bar is not None:
            self.progress_bar.empty()
        if self.status_text is not None:
            self.status_text.empty()
        self.progress_bar = None
        self.status_text = None

# Create a global progress tracker
progress_tracker = ProgressTracker()

async def generate_research(query: str, config: dict) -> tuple[Optional[str], Optional[bytes]]:
    """
    Generate research report and PDF
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            # Health check
            progress_tracker.show_progress("init")
            response = await client.get(f"{API_URL}/")
            if response.status_code != 200:
                st.error("API is not available")
                return None, None

            # Generate markdown report
            progress_tracker.show_progress("search")
            payload = {
                "query": query,
                "max_results": config["max_results"],
                "time_filter": config["time_filter"],
                "output_format": config.get("output_format", "markdown"),
                "title": f"Research Report: {query}"
            }
            
            progress_tracker.show_progress("extract")
            response = await client.post(
                f"{API_URL}/api/research",
                json=payload,
                timeout=120.0
            )
            
            if response.status_code != 200:
                error_message = "Error generating report"
                try:
                    error_detail = response.json().get("detail", str(response.text))
                    error_message = f"{error_message}: {error_detail}"
                except:
                    error_message = f"{error_message}: Status {response.status_code}"
                st.error(error_message)
                return None, None
            
            # Get the markdown content directly from response.text
            content = response.text
            
            if not content:
                st.error("No content received from the API")
                return None, None
            
            progress_tracker.show_progress("complete")
            
            # For PDF requests, return the content as bytes
            if config.get("output_format") == "pdf":
                return None, response.content
            # For markdown requests, return the content as text
            return content, None
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.write("Debug: Full error information", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            return None, None

def render_sidebar_config() -> dict:
    """Render sidebar configuration options"""
    st.sidebar.title("Settings")
    show_config = st.sidebar.toggle("Show Advanced Configuration")
    
    config = DEFAULT_CONFIG.copy()
    
    if show_config:
        st.sidebar.subheader("Advanced Configuration")
        
        # Search settings
        st.sidebar.markdown("#### Search Settings")
        config["max_results"] = st.sidebar.slider("Max Search Results", 1, 20, DEFAULT_CONFIG["max_results"])
        config["time_filter"] = st.sidebar.selectbox("Time Filter", ["day", "week", "month", "year"], 
                                                   index=["day", "week", "month", "year"].index(DEFAULT_CONFIG["time_filter"]))
        
        # Content Processing
        st.sidebar.markdown("#### Content Processing")
        config["chunk_size"] = st.sidebar.number_input("Chunk Size", 100, 2000, DEFAULT_CONFIG["chunk_size"])
        config["chunk_overlap"] = st.sidebar.number_input("Chunk Overlap", 0, 500, DEFAULT_CONFIG["chunk_overlap"])
        config["max_chunks_for_report"] = st.sidebar.number_input("Max Chunks for Report", 1, 20, DEFAULT_CONFIG["max_chunks_for_report"])
        
        # Model Settings
        st.sidebar.markdown("#### Model Settings")
        config["temperature"] = st.sidebar.slider("Temperature", 0.0, 1.0, DEFAULT_CONFIG["temperature"])
        config["max_tokens"] = st.sidebar.number_input("Max Tokens", 1000, 8000, DEFAULT_CONFIG["max_tokens"])
        
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
        
        # Generate report (without PDF initially)
        markdown_content, _ = asyncio.run(generate_research(query, config))
        
        if markdown_content:
            st.session_state.research_output = markdown_content
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
                _, pdf_data = asyncio.run(generate_research(query, config))
                
                progress_tracker.clear()
                
                if pdf_data:
                    st.session_state.pdf_data = pdf_data
                    st.download_button(
                        label="Download PDF Report",
                        data=pdf_data,
                        file_name=f"research_report_{query[:30]}.pdf".replace(" ", "_"),
                        mime="application/pdf",
                        help="Download the report as a PDF file"
                    )
                else:
                    st.error("Failed to generate PDF")

if __name__ == "__main__":
    main() 