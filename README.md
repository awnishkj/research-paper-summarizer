# ResearchIQ: AI-Powered Research Paper Summarizer & Assistant

ResearchIQ is a modern, high-fidelity local web application designed to help researchers, students, and professionals quickly digest long-form scientific papers. By uploading a PDF paper, the system parses the document, uses the Google Gemini API to generate structured technical summaries, and starts a context-grounded chat advisor for real-time Q&A.

## Key Features

- **Drag-and-Drop Parsing**: Instant local text and metadata extraction from PDF files.
- **Three Summary Perspectives**:
  - **TL;DR / Executive Summary**: Focuses on core findings, solutions, and takeaways.
  - **Technical Analysis**: Section-by-section breakdown focusing on methodology, empirical results, and constructive critique.
  - **Key Concepts Map**: Extracts specific models, equations, and glossary definitions for rapid lookup.
- **Interactive Q&A Chat Advisor**: Real-time dialogue grounded strictly in the contents of the uploaded paper to prevent hallucinations.
- **Interactive Recommendation Chips**: Click-to-ask suggestions that answer common academic questions (like explaining the methodology, limitations, or datasets used).
- **Premium User Experience**: Designed using rich cosmic dark theme aesthetics, subtle animations, responsive flex grids, and full markdown rendering.

## Project Structure

```
research-paper-summarizer/
│
├── app.py                 # FastAPI backend server
├── pdf_reader.py          # Local PDF parser (using pypdf)
├── summarizer.py          # Gemini API connector and logic
├── prompts.py             # Prompt engineering and templates
├── requirements.txt       # Python package list
├── README.md              # Project documentation
├── .env                   # Environment config (API Key)
│
├── uploads/               # Holds uploaded files during session
│
└── assets/                # Web application assets
    ├── index.html         # Application dashboard layout
    ├── styles.css         # Glassmorphic dark styling
    └── script.js          # Client-side dynamic state script
```

## Setup & Installation

### 1. Clone or Copy the Project
Ensure all files are placed in a folder named `research-paper-summarizer/` in your workspace.

### 2. Configure a Virtual Environment
It is recommended to run this in a Python virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Or Windows Command Prompt
.\venv\Scripts\activate.bat

# Or Unix/macOS
source venv/bin/activate
```

### 3. Install Dependencies
Install all required libraries specified in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Set Up the Gemini API Key
1. Obtain an API Key from the [Google AI Studio](https://aistudio.google.com/).
2. Open the `.env` file at the root of the project.
3. Replace the placeholder with your actual API key:
   ```env
   GEMINI_API_KEY=AIzaSy...YourActualGeminiKey...
   ```

### 5. Launch the Server
Start the FastAPI server via Uvicorn:
```bash
python -m uvicorn app:app --reload --port 8000
```

### 6. Access the Application
Open your browser and navigate to:
```
http://localhost:8000
```
Drag your research paper into the window, and let ResearchIQ handle the rest!
