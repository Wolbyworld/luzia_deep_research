# Deep Research Assistant Frontend

A Streamlit-based frontend for the Deep Research Assistant.

## Features

- 🎯 Simple and intuitive interface
- ⚙️ Advanced configuration options
- 📊 Real-time progress tracking
- 📄 Markdown and PDF output
- 🔍 Source tracking and linking
- 💡 Helpful configuration tips

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure the backend server is running first:
```bash
cd ../backend
python main.py
```

3. Run the Streamlit app:
```bash
cd frontend/src
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`.

## Configuration

The app provides two levels of configuration:

1. **Basic Mode**
   - Default settings suitable for most use cases
   - Clean, minimal interface

2. **Advanced Mode** (toggle in sidebar)
   - Search settings
   - Content processing parameters
   - Model configuration
   - Detailed tooltips and explanations

## Usage

1. Enter your research question in the text area
2. (Optional) Adjust settings in the sidebar
3. Click "Generate Report"
4. Monitor progress in real-time
5. View the report in markdown format
6. Download as PDF if needed
7. Check sources in the Sources tab

## Environment Variables

The app looks for these environment variables:
- `API_URL`: Backend API URL (default: http://localhost:8000)

You can set them in the backend's `.env` file or your environment. 