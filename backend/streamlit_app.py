import streamlit as st
import httpx
import asyncio
import json
import base64
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize session state
if 'research_output' not in st.session_state:
    st.session_state.research_output = None
if 'pdf_data' not in st.session_state:
    st.session_state.pdf_data = None

# App configuration
API_URL = "http://localhost:8000"

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

async def generate_research(query: str, config: dict) -> tuple[Optional[str], Optional[bytes]]:
    """
    Generate research report and PDF
    """
    async with httpx.AsyncClient() as client:
        try:
            # Health check
            response = await client.get(f"{API_URL}/")
            if response.status_code != 200:
                st.error("API is not available")
                return None, None

            # Generate markdown report
            payload = {
                "query": query,
                "max_results": config["max_results"],
                "time_filter": config["time_filter"],
                "output_format": "markdown",
                "title": f"Research Report: {query}"
            }
            
            response = await client.post(
                f"{API_URL}/api/research",
                json=payload,
                timeout=120.0
            )
            
            if response.status_code != 200:
                st.error(f"Error generating report: {response.text}")
                return None, None
                
            markdown_content = response.text
            
            # Generate PDF version
            payload["output_format"] = "pdf"
            response = await client.post(
                f"{API_URL}/api/research",
                json=payload,
                timeout=120.0
            )
            
            if response.status_code != 200:
                st.error("Error generating PDF")
                return markdown_content, None
                
            return markdown_content, response.content
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None, None

def show_progress(phase: str, progress: int):
    """Update progress bar with current phase"""
    progress_bar.progress(progress)
    status_text.text(f"Phase: {phase}")

def main():
    st.title("Luzia Research Assistant")
    
    # Sidebar - Configuration
    st.sidebar.title("Settings")
    show_config = st.sidebar.toggle("Show Advanced Configuration")
    
    config = DEFAULT_CONFIG.copy()
    
    if show_config:
        st.sidebar.subheader("Advanced Configuration")
        config["max_results"] = st.sidebar.slider("Max Search Results", 1, 20, DEFAULT_CONFIG["max_results"])
        config["time_filter"] = st.sidebar.selectbox("Time Filter", ["day", "week", "month", "year"], 
                                                   index=["day", "week", "month", "year"].index(DEFAULT_CONFIG["time_filter"]))
        config["chunk_size"] = st.sidebar.number_input("Chunk Size", 100, 2000, DEFAULT_CONFIG["chunk_size"])
        config["chunk_overlap"] = st.sidebar.number_input("Chunk Overlap", 0, 500, DEFAULT_CONFIG["chunk_overlap"])
        config["max_chunks_for_report"] = st.sidebar.number_input("Max Chunks for Report", 1, 20, DEFAULT_CONFIG["max_chunks_for_report"])
        config["temperature"] = st.sidebar.slider("Temperature", 0.0, 1.0, DEFAULT_CONFIG["temperature"])
        config["max_tokens"] = st.sidebar.number_input("Max Tokens", 1000, 8000, DEFAULT_CONFIG["max_tokens"])

    # Main content
    query = st.text_area("Enter your research question:", height=100)
    
    if st.button("Generate Report"):
        if not query:
            st.warning("Please enter a research question")
            return
            
        # Initialize progress tracking
        global progress_bar, status_text
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Generate report
        show_progress("Initializing...", 0)
        
        markdown_content, pdf_data = asyncio.run(generate_research(query, config))
        
        if markdown_content:
            st.session_state.research_output = markdown_content
            st.session_state.pdf_data = pdf_data
            
            # Display the report
            st.markdown("## Research Report")
            st.markdown(markdown_content)
            
            # Download buttons
            if pdf_data:
                st.download_button(
                    label="Download PDF",
                    data=pdf_data,
                    file_name="research_report.pdf",
                    mime="application/pdf"
                )
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
        else:
            st.error("Failed to generate report")
            progress_bar.empty()
            status_text.empty()

if __name__ == "__main__":
    main() 