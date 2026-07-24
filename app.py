import os
import shutil
import uuid
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import pdf_reader
import summarizer

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

app = FastAPI(title="ResearchIQ API", description="Backend services for paper summarization and grounded Q&A.")

import json
DB_FILE = os.path.join(BASE_DIR, "db.json")

papers_db: Dict[str, Dict[str, Any]] = {}
general_chats_db: Dict[str, Dict[str, Any]] = {}

def load_db():
    global papers_db, general_chats_db
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                papers_db = data.get("papers", {})
                general_chats_db = data.get("general_chats", {})
                print(f"Loaded {len(papers_db)} papers and {len(general_chats_db)} chats from db.json")
        except Exception as e:
            print("Failed to load db.json, starting empty:", e)
            papers_db = {}
            general_chats_db = {}
    else:
        papers_db = {}
        general_chats_db = {}

def save_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "papers": papers_db,
                "general_chats": general_chats_db
            }, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Failed to save db.json:", e)

@app.on_event("startup")
async def startup_event():
    load_db()

class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatPayload(BaseModel):
    messages: List[Message]

class GeneralChatPayload(BaseModel):
    chat_id: Optional[str] = None
    messages: List[Message]

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Handles PDF uploading, text/meta extraction, and triggers the initial executive summary.
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Check if a paper with the same file name already exists in the database
    for pid, pdata in papers_db.items():
        if pdata.get("metadata", {}).get("file_name") == file.filename:
            return {
                "success": True,
                "paper_id": pid,
                "metadata": pdata["metadata"],
                "initial_summary": pdata["summaries"]["executive"]
            }

    paper_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{paper_id}.pdf")
    
    try:
        # Save file locally
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Extract text and metadata
        extraction = pdf_reader.extract_pdf_data(file_path)
        if not extraction["success"]:
            raise Exception(extraction["error"])
            
        paper_text = extraction["text"]
        
        # Check API Key configuration
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
            raise ValueError("GEMINI_API_KEY is not configured on the backend. Please add it to your .env file.")
            
        # Generate initial executive summary
        exec_summary = summarizer.generate_summary(paper_text, "executive")
        if exec_summary.startswith("Error during summary generation:"):
            raise Exception(exec_summary)
        
        # Save to in-memory database
        papers_db[paper_id] = {
            "text": paper_text,
            "pages": extraction["pages"],
            "metadata": extraction["metadata"],
            "summaries": {
                "executive": exec_summary,
                "structured": None,
                "concepts": None
            },
            "chat_history": []
        }
        
        save_db()
        
        return {
            "success": True,
            "paper_id": paper_id,
            "metadata": extraction["metadata"],
            "initial_summary": exec_summary
        }
        
    except ValueError as val_err:
        # Configuration issues (.env API key missing)
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=501, detail=str(val_err))
        
    except Exception as e:
        # General file or LLM errors
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")

@app.get("/api/papers")
async def get_uploaded_papers():
    """
    Returns a list of all papers uploaded in this session.
    """
    return [
        {
            "paper_id": pid,
            "title": pdata["metadata"]["title"],
            "file_name": pdata["metadata"]["file_name"]
        }
        for pid, pdata in papers_db.items()
    ]

@app.get("/api/paper/{paper_id}")
async def get_paper_details(paper_id: str):
    """
    Returns the metadata and cached summaries for a specific paper.
    """
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found.")
        
    pdata = papers_db[paper_id]
    return {
        "paper_id": paper_id,
        "metadata": pdata["metadata"],
        "summaries": pdata["summaries"],
        "chat_history": pdata.get("chat_history", [])
    }

@app.get("/api/summary/{paper_id}/{summary_type}")
async def get_summary(paper_id: str, summary_type: str):
    """
    Fetches the requested summary type. If not cached, generates and caches it.
    Supported types: 'executive', 'structured', 'concepts'.
    """
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found. Please upload it again.")
        
    valid_types = ["executive", "structured", "concepts"]
    if summary_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid summary type. Choose from {valid_types}")
        
    paper_data = papers_db[paper_id]
    
    # Check cache first
    cached_summary = paper_data["summaries"].get(summary_type)
    if cached_summary and not cached_summary.startswith("Error during summary generation:"):
        return {"summary": cached_summary}
        
    # Generate and cache
    try:
        summary = summarizer.generate_summary(paper_data["text"], summary_type)
        if summary.startswith("Error during summary generation:"):
            raise Exception(summary)
            
        paper_data["summaries"][summary_type] = summary
        save_db()
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating {summary_type} summary: {str(e)}")

@app.get("/api/chats/general")
async def get_general_chats_list():
    """
    Returns the list of all general chat sessions.
    """
    return [
        {"chat_id": cid, "title": cdata["title"]}
        for cid, cdata in general_chats_db.items()
    ]

@app.get("/api/chat/general/{chat_id}")
async def get_general_chat_session(chat_id: str):
    """
    Returns the message history for a specific general chat session.
    """
    if chat_id not in general_chats_db:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return general_chats_db[chat_id]

@app.post("/api/chat/general")
async def general_chat_endpoint(payload: GeneralChatPayload):
    """
    Handles general chat Q&A sessions. Creates a new session if chat_id is missing.
    """
    formatted_messages = [
        {"role": msg.role, "content": msg.content} for msg in payload.messages
    ]
    if not formatted_messages:
        raise HTTPException(status_code=400, detail="Empty chat messages provided.")
        
    chat_id = payload.chat_id
    
    # Generate unique ID if starting a new thread
    if not chat_id or chat_id not in general_chats_db:
        chat_id = str(uuid.uuid4())
        # Find first user query to serve as title
        user_queries = [m["content"] for m in formatted_messages if m["role"] == "user"]
        title = user_queries[0][:30] + "..." if user_queries else "New Chat"
    else:
        title = general_chats_db[chat_id]["title"]
        
    try:
        response_text = summarizer.chat_general(formatted_messages)
        
        # Save session history
        general_chats_db[chat_id] = {
            "chat_id": chat_id,
            "title": title,
            "messages": formatted_messages + [{"role": "assistant", "content": response_text}]
        }
        save_db()
        
        return {
            "chat_id": chat_id,
            "title": title,
            "response": response_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in general chat: {str(e)}")

@app.post("/api/chat/{paper_id}")
async def chat_endpoint(paper_id: str, payload: ChatPayload):
    """
    Accepts full chat history and uses the paper's text to answer questions.
    """
    if paper_id not in papers_db:
        raise HTTPException(status_code=404, detail="Paper not found. Please upload it again.")
        
    paper_data = papers_db[paper_id]
    
    # Format messages for the summarizer
    formatted_messages = [
        {"role": msg.role, "content": msg.content} for msg in payload.messages
    ]
    
    if not formatted_messages:
        raise HTTPException(status_code=400, detail="Empty chat messages provided.")
        
    try:
        response_text = summarizer.chat_with_paper(formatted_messages, paper_data["text"])
        paper_data["chat_history"] = formatted_messages + [{"role": "assistant", "content": response_text}]
        save_db()
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chatting with paper: {str(e)}")
class KeyPayload(BaseModel):
    api_key: str

@app.post("/api/config/key")
async def configure_api_key(payload: KeyPayload):
    """
    Updates the active Gemini API key in the environment and .env file.
    """
    key = payload.api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API key cannot be empty.")
        
    # Update environment variable in memory
    os.environ["GEMINI_API_KEY"] = key
    
    # Write the updated key back to the .env file so it persists across server restarts
    env_path = os.path.join(BASE_DIR, ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        key_updated = False
        for i, line in enumerate(lines):
            if line.startswith("GEMINI_API_KEY="):
                lines[i] = f"GEMINI_API_KEY={key}\n"
                key_updated = True
                break
        if not key_updated:
            lines.append(f"GEMINI_API_KEY={key}\n")
    else:
        lines = [f"GEMINI_API_KEY={key}\n"]
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    # Re-configure summarizer SDK with the new key
    try:
        summarizer.configure_sdk()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid API key structure: {str(e)}")
        
    return {"success": True, "message": "API key successfully updated and saved."}

@app.get("/api/health")
async def health_check():
    """Simple status check."""
    api_key = os.getenv("GEMINI_API_KEY")
    api_configured = api_key is not None and api_key != "YOUR_GEMINI_API_KEY_HERE"
    return {
        "status": "healthy",
        "api_configured": api_configured
    }

# Serve Static Assets
# Note: Mount static files AFTER API endpoints so they don't override routing.
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

@app.get("/")
async def serve_index():
    """Serves the main application page."""
    index_path = os.path.join(ASSETS_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "Welcome to the Research Paper Summarizer API. Please upload a web UI to assets/index.html to view the interface."
    }
