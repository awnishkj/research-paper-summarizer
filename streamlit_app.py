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

# Custom CSS to skin Streamlit elements to match the exact custom FastAPI Web App frontend
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

    /* Overall App View Background */
    .stApp {
        background-color: #f8fafc !important;
    }

    /* Sidebar Styling to match assets/styles.css */
    section[data-testid="stSidebar"] {
        background-color: rgba(255, 255, 255, 0.75) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(15, 23, 42, 0.08) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 14px !important;
        padding-top: 10px !important;
    }

    /* Logo Header Styling */
    .app-header-container {
        display: flex;
        flex-direction: column;
        margin-bottom: 4px;
    }
    .app-logo-title {
        font-family: 'Outfit', sans-serif;
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .app-logo-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 10px;
        font-weight: 600;
        color: #64748b;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin: 0;
    }

    /* Premium card containers */
    .premium-card {
        background: white !important;
        border: 1px solid rgba(15, 23, 42, 0.06) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.02) !important;
        margin-bottom: 20px !important;
    }

    /* History/Recent Document Lists */
    .sidebar-section-title {
        font-family: 'Outfit', sans-serif;
        font-size: 11px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
        margin-top: 10px;
    }
    
    /* Custom style for list button cards */
    div.stButton > button {
        background: white !important;
        color: #334155 !important;
        border: 1px solid rgba(15, 23, 42, 0.06) !important;
        border-radius: 10px !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        padding: 8px 12px !important;
        text-align: left !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.01) !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        display: block !important;
    }
    div.stButton > button:hover {
        border-color: #4f46e5 !important;
        color: #4f46e5 !important;
        background: rgba(79, 70, 229, 0.03) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(79, 70, 229, 0.06) !important;
    }
    
    /* Pill button style specifically for New General Chat */
    div.stButton > button[key*="new_general_chat"] {
        border-radius: 20px !important;
        text-align: center !important;
        border: 1px solid rgba(79, 70, 229, 0.2) !important;
        font-weight: 600 !important;
    }
    
    /* Suggestion chip buttons styling */
    .suggestion-chip button {
        background: rgba(15, 23, 42, 0.02) !important;
        border: 1px solid rgba(15, 23, 42, 0.05) !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        color: #475569 !important;
        padding: 6px 12px !important;
        margin: 4px 0 !important;
    }
    .suggestion-chip button:hover {
        background: rgba(79, 70, 229, 0.05) !important;
        color: #4f46e5 !important;
        border-color: rgba(79, 70, 229, 0.2) !important;
    }

    /* Tab Switcher overrides */
    button[data-baseweb="tab"] {
        font-family: 'Outfit', sans-serif !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #64748b !important;
        border-bottom: 2px solid transparent !important;
        padding: 12px 20px !important;
        transition: all 0.2s ease !important;
    }
    button[aria-selected="true"] {
        color: #4f46e5 !important;
        border-bottom-color: #4f46e5 !important;
    }

    /* Chat bubble bubble custom skin styling */
    div[data-testid="stChatMessage"] {
        background-color: white !important;
        border: 1px solid rgba(15, 23, 42, 0.05) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        margin-bottom: 12px !important;
    }
    
    /* Input field styling */
    div[data-testid="stChatInput"] textarea {
        border-radius: 12px !important;
        border: 1px solid rgba(15, 23, 42, 0.08) !important;
        padding: 12px !important;
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
    # Logo Header Container matching Assets logo
    st.markdown("""
    <div class="app-header-container" style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
        <div style="font-size: 26px;">🧠</div>
        <div>
            <h1 class="app-logo-title" style="margin: 0; line-height: 1.1;">ResearchIQ</h1>
            <p class="app-logo-subtitle" style="margin: 0;">AI-Powered Research Assistant</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
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
        st.success("🔑 API Key configured!")
        if st.button("Change API Key"):
            st.session_state.gemini_api_key = None
            os.environ["GEMINI_API_KEY"] = ""
            st.rerun()
        st.write("---")

    # Sidebar Navigation Buttons
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        if st.button("📄 New Paper", key="btn_upload_nav", use_container_width=True):
            st.session_state.mode = "welcome"
            st.session_state.active_paper_id = None
            st.rerun()
    with col_nav2:
        if st.button("💬 General Chat", key="btn_chat_nav", use_container_width=True):
            st.session_state.mode = "general"
            st.session_state.active_general_chat_id = None
            st.rerun()

    # Recent Documents List (Staged like document cards)
    if st.session_state.papers:
        st.markdown('<div class="sidebar-section-title">Recent Documents</div>', unsafe_allow_html=True)
        for pid, pdata in list(st.session_state.papers.items())[:15]:
            title = pdata["metadata"]["title"]
            if len(title) > 28:
                title = title[:25] + "..."
            btn_label = f"📄 {title}"
            if st.session_state.active_paper_id == pid and st.session_state.mode == "paper":
                btn_label = f"🎯 {title}"
            
            if st.sidebar.button(btn_label, key=f"btn-paper-{pid}"):
                st.session_state.active_paper_id = pid
                st.session_state.mode = "paper"
                st.rerun()

    # General Chat history section
    if st.session_state.general_chats:
        st.markdown('<div class="sidebar-section-title">Recent Chats</div>', unsafe_allow_html=True)
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

    # API Status Indicator fixed at bottom of sidebar
    st.write("---")
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; color: #475569; padding-left: 2px;">
        <span>Gemini API Status:</span>
        <span style="display: inline-block; width: 8px; height: 8px; background-color: #22c55e; border-radius: 50%;"></span>
        <span style="font-weight: 600; color: #16a34a;">Online</span>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN DASHBOARD INTERFACE ---
col_center, col_right = st.columns([2, 1])

# active states configuration
paper_id = st.session_state.active_paper_id
paper_data = st.session_state.papers.get(paper_id) if paper_id else None

# LEFT COLUMN: Center Column (PDF Upload/Welcome or Summaries Tabs)
with col_center:
    if st.session_state.mode == "welcome" or not paper_data:
        # Document Icon
        st.markdown("""
        <div style="display: flex; justify-content: center; margin-top: 15px; margin-bottom: 10px;">
            <div style="background-color: #f1f5f9; border-radius: 50%; width: 56px; height: 56px; display: flex; justify-content: center; align-items: center; font-size: 26px; color: #475569; border: 1px solid rgba(15,23,42,0.06);">
                📄
            </div>
        </div>
        <p style="text-align: center; color: #475569; font-size: 14.5px; margin-bottom: 24px; max-width: 500px; margin-left: auto; margin-right: auto; line-height: 1.5;">
            Upload a PDF research paper to generate automated summaries, extract key concepts, and start chatting with the paper context.
        </p>
        """, unsafe_allow_html=True)

        # Drag & drop PDF uploader
        uploaded_file = st.file_uploader("Drag & drop your PDF here", type=["pdf"], key="main_pdf_uploader")
        if uploaded_file is not None:
            # Check if this is a newly uploaded file
            if st.session_state.get("last_processed_file") != uploaded_file.name:
                # Check if already processed
                existing_id = None
                for pid, pdata in st.session_state.papers.items():
                    if pdata.get("metadata", {}).get("file_name") == uploaded_file.name:
                        existing_id = pid
                        break
                        
                if existing_id:
                    st.session_state.active_paper_id = existing_id
                    st.session_state.mode = "paper"
                    st.session_state.last_processed_file = uploaded_file.name
                    st.success("Loaded from cache!")
                    st.rerun()
                else:
                    with st.spinner("Processing PDF and generating executive summary..."):
                        temp_id = str(uuid.uuid4())
                        file_path = os.path.join(UPLOAD_DIR, f"{temp_id}.pdf")
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        extraction = pdf_reader.extract_pdf_data(file_path)
                        if extraction["success"]:
                            exec_summary = summarizer.generate_summary(extraction["text"], "executive")
                            st.session_state.papers[temp_id] = {
                                "text": extraction["text"],
                                "pages": extraction["pages"],
                                "metadata": {
                                    "title": extraction["metadata"]["title"] or uploaded_file.name,
                                    "file_name": uploaded_file.name,
                                    "author": extraction["metadata"]["author"] or "Unknown Author",
                                    "subject": extraction["metadata"]["subject"] or "Academic Research",
                                    "pages_count": extraction["metadata"]["pages_count"]
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
                            st.session_state.last_processed_file = uploaded_file.name
                            st.rerun()
                        else:
                            st.error(f"Failed to read PDF: {extraction['error']}")
        else:
            # Clear last processed file state if uploader is cleared
            st.session_state.last_processed_file = None

        st.write("---")

        # General AI Research Assistant Panel
        st.markdown('<h4 style="font-family: \'Outfit\', sans-serif; font-weight: 700; color: #0f172a; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">💬 General AI Research Assistant</h4>', unsafe_allow_html=True)
        
        chat_id = st.session_state.active_general_chat_id
        chat_data = st.session_state.general_chats.get(chat_id, {"messages": []})
        
        general_chat_container = st.container()
        with general_chat_container:
            if not chat_data["messages"]:
                st.markdown("""
                <div style="background-color: #f8fafc; border: 1px solid rgba(15, 23, 42, 0.05); border-radius: 12px; padding: 16px; color: #334155; font-size: 13.5px; margin-bottom: 12px; border-left: 4px solid #4f46e5;">
                    👋 <strong>Hello!</strong> I am your general research helper. You can ask me general questions, clarify scientific terms, or outline study topics before loading a paper.
                </div>
                """, unsafe_allow_html=True)
            else:
                for msg in chat_data["messages"]:
                    render_chat_message(msg["role"], msg["content"])

        user_input = st.chat_input("Ask a general question...", key="general_chat_input")
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
                st.session_state.mode = "general"
                
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
        # Document loaded: display Summaries Tabs
        st.markdown(f"## 📄 {paper_data['metadata']['title']}")
        st.markdown(
            f"**Author:** {paper_data['metadata']['author']} | "
            f"**Pages:** {paper_data['metadata']['pages_count']} | "
            f"**Subject:** {paper_data['metadata']['subject']}"
        )
        
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

# RIGHT COLUMN: Paper Assistant Column (Persistent)
with col_right:
    st.markdown('<h3 style="font-family: \'Outfit\', sans-serif; font-weight: 700; color: #0f172a; margin-bottom: 2px;">📋 Paper Assistant</h3>', unsafe_allow_html=True)
    st.markdown('<p style="color: #64748b; font-size: 12px; margin-bottom: 16px;">Grounded in paper context</p>', unsafe_allow_html=True)
    st.write("---")
    
    if paper_data:
        # Chat history container
        chat_container = st.container()
        with chat_container:
            for msg in paper_data["chat_history"]:
                render_chat_message(msg["role"], msg["content"])
                
        # Interactive Suggestion Chips
        st.markdown("###### Suggestion Queries:")
        col_chip1, col_chip2 = st.columns(2)
        with col_chip1:
            st.markdown('<div class="suggestion-chip">', unsafe_allow_html=True)
            if st.button("💡 Explain core problem", key="chip_prob"):
                paper_data["chat_history"].append({"role": "user", "content": "Explain the core problem of this paper in simple terms."})
                save_persistent_db()
                st.rerun()
            if st.button("📊 Datasets & parameters", key="chip_data"):
                paper_data["chat_history"].append({"role": "user", "content": "What are the datasets, configurations, and parameters used in this paper?"})
                save_persistent_db()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with col_chip2:
            st.markdown('<div class="suggestion-chip">', unsafe_allow_html=True)
            if st.button("⚙️ Simple Methodology", key="chip_method"):
                paper_data["chat_history"].append({"role": "user", "content": "Explain the methodology of this paper in simple terms."})
                save_persistent_db()
                st.rerun()
            if st.button("⚠️ Critical limitations", key="chip_limit"):
                paper_data["chat_history"].append({"role": "user", "content": "What are the critical limitations or assumptions of this paper?"})
                save_persistent_db()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("---")
        
        # Chat input
        user_question = st.chat_input("Ask a question about this paper...", key="paper_chat_input")
        if user_question:
            paper_data["chat_history"].append({"role": "user", "content": user_question})
            save_persistent_db()
            st.rerun()
            
        # Response generation
        if paper_data["chat_history"] and paper_data["chat_history"][-1]["role"] == "user":
            with st.spinner("Thinking..."):
                response = summarizer.chat_with_paper(paper_data["chat_history"], paper_data["text"])
                paper_data["chat_history"].append({"role": "assistant", "content": response})
                save_persistent_db()
                st.rerun()
    else:
        # Welcome advisor bubble when empty
        st.markdown("""
        <div style="background-color: #f8fafc; border: 1px solid rgba(15, 23, 42, 0.05); border-radius: 12px; padding: 16px; color: #334155; font-size: 13.5px; margin-bottom: 20px; border-left: 4px solid #7c3aed; line-height: 1.5;">
            👋 <strong>Hello!</strong> I am your research advisor. Upload a research paper, and I can help answer specific questions, explain complex math, locate datasets, or elaborate on their results.
        </div>
        """, unsafe_allow_html=True)
        
        # Disabled chat input box placeholder
        st.chat_input("Ask a question about this paper... (Upload a paper first)", disabled=True, key="disabled_chat_input")
