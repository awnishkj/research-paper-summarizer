# 🔬 ResearchIQ
> **AI-Powered Research Paper Summarizer & Advisor**

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-4F46E5?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Python](https://img.shields.io/badge/Python%203.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

---

**ResearchIQ** is a premium, locally-hosted web application that leverages the power of Google Gemini AI to analyze, summarize, and explain complex academic and scientific papers. Drag, drop, and instantly convert dense PDF publications into structured summaries and interactive, grounded Q&A threads.

---

## ✨ Features

- 📂 **Drag & Drop PDF Parser**: Instantly extracts full text and publication metadata locally.
- 🧠 **Chain-of-Thought Reasoning**: Integrates collapsible `Thinking Process` dropdowns showing exactly how the AI retrieves and parses mathematical equations and scientific assertions.
- 💬 **Grounded Q&A Advisor**: Ask questions directly about the paper's contents with zero hallucination.
- 📋 **Three Specialized Perspectives**:
  - **💡 TL;DR / Executive Summary**: Get high-level takeaways, core problems, and solutions in plain language.
  - **📊 Structured Technical Analysis**: Deep dives into systems, datasets, empirical outcomes, and limitations.
  - **🧩 Key Concepts Glossary**: Cards detailing definitions and context-indicators for specific terminology.
- 🎨 **Cosmic Slate Theme**: Designed with a high-fidelity glassmorphic layout, hover effects, and full markdown text rendering.
- 🔍 **One-Click Query Chips**: Pre-configured recommendation triggers to quickly inspect datasets, limitations, or core methodology.

---

## 🛠️ Architecture

```
research-paper-summarizer/
├── app.py                 # FastAPI backend server
├── pdf_reader.py          # Local PDF parser (using pypdf)
├── summarizer.py          # Gemini API wrapper and logic
├── prompts.py             # Prompt engineering and templates
├── requirements.txt       # Python package list
├── .env                   # Environment config (API Key)
└── assets/                # Web application assets
    ├── index.html         # Application dashboard layout
    ├── styles.css         # Glassmorphic dark styling
    └── script.js          # Client-side dynamic state script
```

---

## 🚀 Quick Start

### 1. Navigate to Project
Ensure all files are placed in a folder named `research-paper-summarizer/`:
```bash
cd research-paper-summarizer
```

### 2. Configure Virtual Environment
It is recommended to run this in a Python virtual environment:
```bash
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate it (macOS/Linux)
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Add Gemini API Key
1. Get an API Key from [Google AI Studio](https://aistudio.google.com/).
2. Create or open `.env` at the root of the project:
```env
GEMINI_API_KEY=AQ.Ab8RN6...YourKeyHere
PORT=8000
HOST=127.0.0.1
```

### 5. Launch the Server
```bash
python -m uvicorn app:app --reload --port 8000
```

Open your browser and navigate to **[http://localhost:8000](http://localhost:8000)**!
