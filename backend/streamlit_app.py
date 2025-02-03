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
if 'sub_reports' not in st.session_state:
    st.session_state.sub_reports = None
if 'research_plan' not in st.session_state:
    st.session_state.research_plan = None

# App configuration
API_URL = "http://localhost:8000"

# Default configuration
DEFAULT_CONFIG = {
    # Search Settings
    "max_results": 5,
    "time_filter": "month",
    
    # Content Processing
    "chunk_size": 1000,
    "chunk_overlap": 100,
    "min_chunk_length": 100,
    "max_chunks_for_report": 10,
    
    # Model Settings
    "temperature": 0.3,
    "max_tokens": 4000,
    
    # Pro Mode Settings
    "max_questions": 4,
    "research_depth": 3,
    "reasoning_effort": "medium"
}

async def generate_research(query: str, config: dict, is_pro_mode: bool = False) -> tuple[Optional[str], Optional[bytes], Optional[list], Optional[list]]:
    """
    Generate research report and PDF
    """
    async with httpx.AsyncClient() as client:
        try:
            # Health check
            response = await client.get(f"{API_URL}/")
            if response.status_code != 200:
                st.error("API is not available")
                return None, None, None, None

            # Generate report with progress updates
            payload = {
                "query": query,
                "max_results": config["max_results"],
                "time_filter": config["time_filter"],
                "output_format": "markdown",
                "title": f"Research Report: {query}",
                "is_pro_mode": is_pro_mode,
                "max_questions": config.get("max_questions", 4)
            }
            
            # Connect to SSE endpoint for progress updates
            async with client.stream('POST', f"{API_URL}/api/research/stream", json=payload, timeout=300.0) as response:
                if response.status_code != 200:
                    st.error(f"Error generating report: {response.text}")
                    return None, None, None, None
                
                result = None
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        data = json.loads(line[6:])
                        if 'progress' in data:
                            show_progress(data['phase'], data['progress'])
                        elif 'result' in data:
                            result = data['result']
                
                if not result:
                    st.error("No result received from the API")
                    return None, None, None, None
                
                markdown_content = result["final_report"]
                sub_reports = result.get("sub_reports", [])
                research_plan = result.get("research_plan", [])
            
            # Generate PDF version
            payload["output_format"] = "pdf"
            response = await client.post(
                f"{API_URL}/api/research",
                json=payload,
                timeout=300.0
            )
            
            if response.status_code != 200:
                st.error("Error generating PDF")
                return markdown_content, None, sub_reports, research_plan
                
            return markdown_content, response.content, sub_reports, research_plan
            
        except Exception as e:
            st.error(f"Error: {str(e)}")
            return None, None, None, None

def update_progress(phase: str, progress: int):
    """Update progress bar and status text with current phase"""
    if 'progress_bar' not in st.session_state:
        st.session_state.progress_bar = st.progress(0)
    if 'status_text' not in st.session_state:
        st.session_state.status_text = st.empty()
    if 'plan_status' not in st.session_state:
        st.session_state.plan_status = st.empty()
    if 'current_query' not in st.session_state:
        st.session_state.current_query = st.empty()
    
    # Update progress bar
    st.session_state.progress_bar.progress(progress)
    st.session_state.status_text.text(f"Phase: {phase}")
    
    # Extract query number and text if it's a research query
    if "Researching query" in phase:
        import re
        match = re.search(r'query (\d+)/(\d+): (.*)', phase)
        if match:
            current, total, query_text = match.groups()
            st.session_state.plan_status.markdown("✅ Research plan generated")
            st.session_state.current_query.markdown(f"🔍 Query {current}/{total}: **{query_text}**")
    elif "Research plan generated" in phase:
        st.session_state.plan_status.markdown("✅ Research plan generated")
        st.session_state.current_query.markdown("⏳ Preparing to execute research plan...")
    elif "Generating research plan" in phase:
        st.session_state.plan_status.markdown("⏳ Generating research plan...")
        st.session_state.current_query.markdown("🔍 Analyzing query...")
    elif "Compiling" in phase:
        st.session_state.plan_status.markdown("✅ Research plan completed")
        st.session_state.current_query.markdown("📝 Compiling final report...")
    elif "complete" in phase.lower():
        st.session_state.plan_status.markdown("✅ Research complete")
        st.session_state.current_query.markdown("✨ Finalizing report...")

def show_progress(phase: str, progress: int):
    """Update progress bar with current phase"""
    update_progress(phase, progress)

def main():
    # Title
    st.title("Luzia Research Agent")
    
    st.markdown("Generate comprehensive research reports from your questions using AI. Advanced settings are available in the sidebar for fine-tuning the research process.")
    
    # Initialize config first
    config = DEFAULT_CONFIG.copy()
    
    # Sidebar - Configuration
    st.sidebar.title("Settings")
    show_config = st.sidebar.checkbox("Show Advanced Configuration", help="Show additional configuration options")
    
    # Pro mode toggle right after the description
    is_pro_mode = st.checkbox("🔍 Enable Pro Mode", key='pro_mode', 
                            help="Break down your query into sub-questions for more comprehensive research")
    
    if show_config:
        st.sidebar.subheader("Advanced Configuration")
        
        st.sidebar.markdown("### Search Settings")
        config["max_results"] = st.sidebar.slider("Max Search Results", 1, 50, DEFAULT_CONFIG["max_results"])
        config["time_filter"] = st.sidebar.selectbox("Time Filter", ["day", "week", "month", "year"], 
                                                   index=["day", "week", "month", "year"].index(DEFAULT_CONFIG["time_filter"]))
        
        st.sidebar.markdown("### Content Processing")
        config["chunk_size"] = st.sidebar.number_input("Chunk Size", 100, 2000, DEFAULT_CONFIG["chunk_size"])
        config["chunk_overlap"] = st.sidebar.number_input("Chunk Overlap", 0, 500, DEFAULT_CONFIG["chunk_overlap"])
        config["max_chunks_for_report"] = st.sidebar.number_input("Max Chunks for Report", 1, 20, DEFAULT_CONFIG["max_chunks_for_report"])
        
        st.sidebar.markdown("### Model Settings")
        config["temperature"] = st.sidebar.slider("Temperature", 0.0, 1.0, DEFAULT_CONFIG["temperature"])
        config["max_tokens"] = st.sidebar.number_input("Max Output Tokens", 1000, 16000, DEFAULT_CONFIG["max_tokens"])

        # Pro Mode Settings section
        if is_pro_mode:  # Only show if pro mode is enabled
            st.sidebar.markdown("### Pro Mode Settings")
            with st.sidebar.expander("Pro Mode Configuration", expanded=True):
                config["max_questions"] = st.number_input(
                    "Max Research Questions", 
                    min_value=2,
                    max_value=8,
                    value=DEFAULT_CONFIG["max_questions"],
                    help="Maximum number of sub-questions to break down the main query into"
                )
                config["research_depth"] = st.slider(
                    "Research Depth",
                    min_value=1,
                    max_value=5,
                    value=3,
                    help="Higher values will generate more detailed sub-reports (1=Quick, 5=Comprehensive)"
                )
                config["reasoning_effort"] = st.selectbox(
                    "Reasoning Effort",
                    options=["low", "medium", "high"],
                    index=1,
                    help="Controls how much effort the AI puts into breaking down the query"
                )

    # Main content area
    input_container = st.container()
    output_container = st.container()

    with input_container:
        query = st.text_area("Enter your research question and press Enter:", 
                    placeholder="Example: What are the latest developments in quantum computing?",
                    height=100,
                    key="query")
        
        # Custom styling for the button to match the screenshot exactly
        st.markdown("""
            <style>
            div.stButton > button:first-child {
                background-color: #ff5c5c;
                color: white;
                border: none;
                padding: 0.5em 0;
                font-size: 16px;
                width: 100%;
                border-radius: 4px;
            }
            div.stButton > button:hover {
                background-color: #ff3333;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Generate button
        generate_button = st.button("Report", use_container_width=True)

    with output_container:
        if generate_button:
            if not query:
                st.warning("Please enter a research question")
                return
                
            # Initialize progress tracking
            st.session_state.progress_bar = st.progress(0)
            st.session_state.status_text = st.empty()
            st.session_state.plan_status = st.empty()
            st.session_state.current_query = st.empty()
            
            # Generate report
            show_progress("Generating research plan...", 0)
            
            markdown_content, pdf_data, sub_reports, research_plan = asyncio.run(
                generate_research(query, config, is_pro_mode=is_pro_mode)
            )
            
            if markdown_content:
                st.session_state.research_output = markdown_content
                st.session_state.pdf_data = pdf_data
                st.session_state.sub_reports = sub_reports
                st.session_state.research_plan = research_plan
                
                # Display research plan if in pro mode
                if is_pro_mode and research_plan:
                    st.markdown("## Research Plan")
                    for i, question in enumerate(research_plan, 1):
                        st.markdown(f"{i}. {question}")
                    st.markdown("---")
                
                # Display the main report
                st.markdown("## Research Report")
                st.markdown(markdown_content)
                
                # Display sub-reports in expandable sections if in pro mode
                if is_pro_mode and sub_reports:
                    st.markdown("## Detailed Research Findings")
                    for i, report in enumerate(sub_reports, 1):
                        with st.expander(f"Research Query {i}: {report['query']}"):
                            st.markdown(report['content'])
                
                # Download buttons
                if pdf_data:
                    st.download_button(
                        label="Download PDF",
                        data=pdf_data,
                        file_name="research_report.pdf",
                        mime="application/pdf"
                    )
            else:
                st.error("Failed to generate report. Please try again.")

if __name__ == "__main__":
    main() 