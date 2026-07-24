import streamlit as st
import os
import uuid
import json
import shutil
import re
import pdf_reader
import summarizer
import streamlit.components.v1 as components
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="ResearchIQ",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=True)

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Persistent DB path
DB_FILE = os.path.join(BASE_DIR, "db.json")

# Initialize session states
if "papers" not in st.session_state:
    st.session_state.papers = {}
if "general_chats" not in st.session_state:
    st.session_state.general_chats = {}
if "active_paper_id" not in st.session_state:
    st.session_state.active_paper_id = None
if "active_general_chat_id" not in st.session_state:
    st.session_state.active_general_chat_id = None
if "mode" not in st.session_state:
    st.session_state.mode = "welcome"  # 'welcome', 'paper', 'general'

# Helper: Load local database
def load_persistent_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.session_state.papers = data.get("papers", {})
                st.session_state.general_chats = data.get("general_chats", {})
        except Exception as e:
            st.error(f"Failed to load local database: {e}")

# Helper: Save local database
def save_persistent_db():
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "papers": st.session_state.papers,
                "general_chats": st.session_state.general_chats
            }, f, indent=4, ensure_ascii=False)
    except Exception as e:
        st.error(f"Failed to save local database: {e}")

# Load DB on startup
load_persistent_db()

# Configure API Key from Secrets, Env, or Session State
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not st.session_state.gemini_api_key:
        try:
            st.session_state.gemini_api_key = st.secrets["GEMINI_API_KEY"]
        except Exception:
            pass

# Keep environment variable in sync
if st.session_state.gemini_api_key:
    os.environ["GEMINI_API_KEY"] = st.session_state.gemini_api_key

# Custom styling for premium aesthetic
st.markdown("""
<style>
    /* Premium font imports */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
    }

    /* Gradient header styling */
    .app-header {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        margin-bottom: 2px;
    }
    
    .app-subtitle {
        color: #64748b;
        font-size: 14px;
        margin-bottom: 24px;
    }

    /* Card design system */
    .premium-card {
        background: white;
        border: 1px solid rgba(15, 23, 42, 0.06);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px -1px rgba(0, 0, 0, 0.01);
        margin-bottom: 16px;
    }

    /* Thinking process card styling */
    .thinking-summary {
        background: rgba(15, 23, 42, 0.02) !important;
        border-left: 3px solid #7c3aed !important;
        border-radius: 6px !important;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# Helper: Render Markdown text with math formatting
def render_content(text):
    if not text:
        return ""
        
    # Replace latex math brackets back to standard $ for Streamlit's markdown engine
    formatted_text = text.replace(r"\(", "$").replace(r"\)", "$")
    formatted_text = formatted_text.replace(r"\[", "$$").replace(r"\]", "$$")
    
    # Render Mermaid.js blocks in custom component if present
    parts = re.split(r"(```mermaid\n.*?\n```)", formatted_text, flags=re.DOTALL)
    for part in parts:
        if part.startswith("```mermaid"):
            # Extract Mermaid code
            mermaid_code = part.replace("```mermaid\n", "").replace("\n```", "").strip()
            # Embed Mermaid rendering
            html_code = f"""
            <div class="mermaid" style="display: flex; justify-content: center; align-items: center; overflow-x: auto; background: #fafafa; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;">
                {mermaid_code}
            </div>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <script>
                mermaid.initialize({{ startOnLoad: true, theme: 'default', securityLevel: 'loose' }});
            </script>
            """
            components.html(html_code, height=450, scrolling=True)
        else:
            # Standard markdown with MathJax support
            st.markdown(part)

# Helper: Render chatbot messages with collapsible CoT blocks
def render_chat_message(role, content):
    with st.chat_message(role):
        # Extract Chain of Thought details block
        cot_match = re.search(r"<details>.*?<summary>🧠 Thinking Process</summary>(.*?)</details>", content, re.DOTALL)
        if cot_match:
            thinking_text = cot_match.group(1).strip()
            # Display collapsible thinking block
            with st.expander("🧠 Thinking Process"):
                st.markdown(f"```\n{thinking_text}\n```")
            # Remove details block from main text
            main_text = re.sub(r"<details>.*?</details>", "", content, flags=re.DOTALL).strip()
        else:
            main_text = content
            
        render_content(main_text)

# --- SIDEBAR CONTROLLERS ---
with st.sidebar:
    st.markdown('<h1 class="app-header">🧠 ResearchIQ</h1>', unsafe_allow_html=True)
    st.markdown('<p class="app-subtitle">AI-POWERED ACADEMIC COPILOT</p>', unsafe_allow_html=True)
    st.write("---")

    # API Key configuration
    if not st.session_state.gemini_api_key:
        st.warning("⚠️ Gemini API key is missing. Paste it below to start:")
        user_key = st.text_input("Enter API Key", type="password")
        if user_key:
            st.session_state.gemini_api_key = user_key
            os.environ["GEMINI_API_KEY"] = user_key
            st.rerun()
        st.write("---")
    else:
        # Show key status inside sidebar
        st.success("🔑 API Key configured!")
        if st.button("Change API Key"):
            st.session_state.gemini_api_key = None
            os.environ["GEMINI_API_KEY"] = ""
            st.rerun()
        st.write("---")

    # Document Uploader
    st.markdown("### 📄 Upload New Paper")
    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], label_visibility="collapsed")
    if uploaded_file is not None:
        # Check if already processed
        existing_id = None
        for pid, pdata in st.session_state.papers.items():
            if pdata.get("metadata", {}).get("file_name") == uploaded_file.name:
                existing_id = pid
                break
                
        if existing_id:
            st.session_state.active_paper_id = existing_id
            st.session_state.mode = "paper"
            st.success("Loaded from persistent cache!")
        else:
            with st.spinner("Processing PDF and generating executive summary..."):
                # Save uploaded file
                temp_id = str(uuid.uuid4())
                file_path = os.path.join(UPLOAD_DIR, f"{temp_id}.pdf")
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Extract PDF text
                extraction = pdf_reader.extract_pdf_data(file_path)
                if extraction["success"]:
                    # Generate TL;DR Executive summary
                    exec_summary = summarizer.generate_summary(extraction["text"], "executive")
                    
                    st.session_state.papers[temp_id] = {
                        "text": extraction["text"],
                        "pages": extraction["pages"],
                        "metadata": {
                            "title": extraction["metadata"]["title"] or uploaded_file.name,
                            "file_name": uploaded_file.name,
                            "author": extraction["metadata"]["author"] or "Unknown Author",
                            "subject": extraction["metadata"]["subject"] or "Academic Research",
                            "pages_count": extraction["pages"]
                        },
                        "summaries": {
                            "executive": exec_summary,
                            "structured": None,
                            "concepts": None
                        },
                        "chat_history": []
                    }
                    save_persistent_db()
                    st.session_state.active_paper_id = temp_id
                    st.session_state.mode = "paper"
                    st.success("Successfully summarized!")
                    st.rerun()
                else:
                    st.error(f"Failed to read PDF: {extraction['error']}")

    st.write("---")

    # Recent Documents List
    if st.session_state.papers:
        st.markdown("### 📁 Recent Documents")
        for pid, pdata in list(st.session_state.papers.items())[:15]:
            title = pdata["metadata"]["title"]
            if len(title) > 28:
                title = title[:25] + "..."
            # Highlight active document button
            btn_label = f"📄 {title}"
            if st.session_state.active_paper_id == pid and st.session_state.mode == "paper":
                btn_label = f"🎯 {title}"
            
            if st.sidebar.button(btn_label, key=f"btn-paper-{pid}"):
                st.session_state.active_paper_id = pid
                st.session_state.mode = "paper"
                st.rerun()

    # General Chat section
    st.write("---")
    st.markdown("### 🤖 Assistant Copilot")
    if st.sidebar.button("💬 New General Chat", use_container_width=True):
        st.session_state.mode = "general"
        st.session_state.active_general_chat_id = None
        st.rerun()
        
    if st.session_state.general_chats:
        st.markdown("#### Recent Chats")
        for cid, cdata in list(st.session_state.general_chats.items())[:15]:
            title = cdata["title"]
            if len(title) > 28:
                title = title[:25] + "..."
            btn_label = f"💬 {title}"
            if st.session_state.active_general_chat_id == cid and st.session_state.mode == "general":
                btn_label = f"👉 {title}"
                
            if st.sidebar.button(btn_label, key=f"btn-chat-{cid}"):
                st.session_state.active_general_chat_id = cid
                st.session_state.mode = "general"
                st.rerun()

# --- MAIN DASHBOARD INTERFACE ---
if st.session_state.mode == "paper" and st.session_state.active_paper_id:
    # 3-Column Layout: Column 1 is sidebar (defined above), main splits into Summary Panel (2/3) and chat assistant (1/3)
    col_summary, col_chat = st.columns([2, 1])
    
    paper_id = st.session_state.active_paper_id
    paper_data = st.session_state.papers[paper_id]
    
    # MAIN COLUMN: Tab Panels
    with col_summary:
        st.markdown(f"## 📄 {paper_data['metadata']['title']}")
        st.markdown(
            f"**Author:** {paper_data['metadata']['author']} | "
            f"**Pages:** {paper_data['metadata']['pages_count']} | "
            f"**Subject:** {paper_data['metadata']['subject']}"
        )
        
        # Tabs for Summaries
        tab_tldr, tab_tech, tab_concepts = st.tabs(["⚡ TL;DR / Executive", "🔬 Technical Analysis", "📚 Key Concepts Map"])
        
        with tab_tldr:
            render_content(paper_data["summaries"]["executive"])
            
        with tab_tech:
            if not paper_data["summaries"]["structured"]:
                with st.spinner("Analyzing methodology and generating technical details..."):
                    summary = summarizer.generate_summary(paper_data["text"], "structured")
                    if not summary.startswith("Error"):
                        st.session_state.papers[paper_id]["summaries"]["structured"] = summary
                        save_persistent_db()
                        st.rerun()
                    else:
                        st.error(summary)
            else:
                render_content(paper_data["summaries"]["structured"])
                
        with tab_concepts:
            if not paper_data["summaries"]["concepts"]:
                with st.spinner("Extracting concepts and compiling relations map..."):
                    summary = summarizer.generate_summary(paper_data["text"], "concepts")
                    if not summary.startswith("Error"):
                        st.session_state.papers[paper_id]["summaries"]["concepts"] = summary
                        save_persistent_db()
                        st.rerun()
                    else:
                        st.error(summary)
            else:
                render_content(paper_data["summaries"]["concepts"])

    # RIGHT COLUMN: Grounded Chat Assistant
    with col_chat:
        st.markdown("### 🤖 Paper Assistant")
        st.caption("Answers are grounded strictly in the paper context")
        st.write("---")
        
        # Chat container height styling
        chat_container = st.container()
        with chat_container:
            for msg in paper_data["chat_history"]:
                render_chat_message(msg["role"], msg["content"])
                
        # Question input
        user_question = st.chat_input("Ask a question about this paper...")
        if user_question:
            # Append query immediately
            paper_data["chat_history"].append({"role": "user", "content": user_question})
            save_persistent_db()
            st.rerun()
            
    # Process message generation if last message was from user
    if paper_data["chat_history"] and paper_data["chat_history"][-1]["role"] == "user":
        with col_chat:
            with st.spinner("Thinking..."):
                response = summarizer.chat_with_paper(paper_data["chat_history"], paper_data["text"])
                paper_data["chat_history"].append({"role": "assistant", "content": response})
                save_persistent_db()
                st.rerun()

elif st.session_state.mode == "general":
    # General Assistant Mode
    st.markdown("## 🤖 AI Research Copilot")
    st.caption("General chat copilot. Use for academic questions, code examples, or research outlines.")
    st.write("---")
    
    chat_id = st.session_state.active_general_chat_id
    chat_data = None
    if chat_id:
        chat_data = st.session_state.general_chats[chat_id]
    else:
        chat_data = {"messages": []}
        
    # Render messages
    for msg in chat_data["messages"]:
        render_chat_message(msg["role"], msg["content"])
        
    user_input = st.chat_input("Ask a research question...")
    if user_input:
        if not chat_id:
            chat_id = str(uuid.uuid4())
            st.session_state.active_general_chat_id = chat_id
            st.session_state.general_chats[chat_id] = {
                "chat_id": chat_id,
                "title": user_input[:28] + "..." if len(user_input) > 28 else user_input,
                "messages": []
            }
            chat_data = st.session_state.general_chats[chat_id]
            
        chat_data["messages"].append({"role": "user", "content": user_input})
        save_persistent_db()
        st.rerun()
        
    if chat_data["messages"] and chat_data["messages"][-1]["role"] == "user":
        with st.spinner("Thinking..."):
            response = summarizer.chat_general(chat_data["messages"])
            chat_data["messages"].append({"role": "assistant", "content": response})
            save_persistent_db()
            st.rerun()

else:
    # Welcome / Blank State
    st.markdown("## Welcome to ResearchIQ 🧠")
    st.markdown("Upload a scientific PDF paper in the sidebar or start a general chat thread to begin.")
    
    # Visual feature list card
    st.markdown("""
    <div class="premium-card">
        <h4>Available Features:</h4>
        <ul>
            <li>⚡ <strong>Executive Summarizer</strong>: Get instant TL;DR bullet points.</li>
            <li>🔬 <strong>Deep Technical Analysis</strong>: Grasp methodology, datasets, parameters, and results immediately.</li>
            <li>📚 <strong>Key Concepts Glossary</strong>: Explore definitions mapping out complex terminology.</li>
            <li>📊 <strong>Auto-Render Diagrams</strong>: Compiles visual Mermaid flowcharts and system workflows.</li>
            <li>📝 <strong>Equation Formatting</strong>: Displays LaTeX formulas dynamically in publication-grade typesetting.</li>
            <li>🤖 <strong>Context-Grounded Q&A</strong>: Ask details regarding formulas or datasets directly.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
