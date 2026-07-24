import os
import re
from pypdf import PdfReader

def extract_pdf_data(file_path: str) -> dict:
    """
    Extracts text and metadata from a PDF file.
    
    Args:
        file_path (str): Absolute path to the PDF file.
        
    Returns:
        dict: A dictionary containing:
            - "success": bool
            - "error": str or None
            - "text": full extracted text
            - "pages": list of strings (text per page)
            - "metadata": dict with title, author, subject, pages_count
    """
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "text": "",
            "pages": [],
            "metadata": {}
        }
        
    try:
        reader = PdfReader(file_path)
        pages_count = len(reader.pages)
        
        pages_text = []
        full_text_list = []
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            # Clean up light formatting artifacts
            text_cleaned = re.sub(r'\s+', ' ', text).strip()
            pages_text.append(text_cleaned)
            full_text_list.append(text)
            
        full_text = "\n\n".join(full_text_list)
        
        # Read standard PDF metadata
        pdf_meta = reader.metadata or {}
        
        title = pdf_meta.get("/Title", "")
        author = pdf_meta.get("/Author", "")
        subject = pdf_meta.get("/Subject", "")
        
        # If title is missing or generic, try to guess from the first page text
        if not title or len(title.strip()) < 3:
            title = _guess_title_from_text(pages_text)
            
        if not author or len(author.strip()) < 3:
            author = pdf_meta.get("/Creator", "Unknown Author")
            
        # Standardize empty strings
        title = str(title).strip() or os.path.basename(file_path).replace(".pdf", "").replace("_", " ").title()
        author = str(author).strip() or "Unknown Author"
        subject = str(subject).strip() or "Academic / Research Paper"
        
        return {
            "success": True,
            "error": None,
            "text": full_text,
            "pages": pages_text,
            "metadata": {
                "title": title,
                "author": author,
                "subject": subject,
                "pages_count": pages_count,
                "file_name": os.path.basename(file_path)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "pages": [],
            "metadata": {}
        }

def _guess_title_from_text(pages_text: list) -> str:
    """
    Attempts to guess the title of the paper using the text on the first page.
    Usually the title is in the first few lines of text.
    """
    if not pages_text:
        return ""
        
    first_page = pages_text[0]
    # Split first page text by lines or full stops to find candidate headings
    lines = [line.strip() for line in first_page.split("\n") if line.strip()]
    if not lines:
        # If it was split by spaces, let's look at the first few words or split by punctuation
        lines = [part.strip() for part in re.split(r'[,.!?]', first_page) if part.strip()]
        
    # Filter out very short lines, page numbers, journal meta headers (like arXiv)
    candidates = []
    for line in lines[:5]:  # Look at first 5 lines/sentences
        if len(line) < 10:
            continue
        if any(keyword in line.lower() for keyword in ["arxiv", "journal", "abstract", "proceeding", "vol.", "no.", "issn", "http"]):
            continue
        candidates.append(line)
        
    if candidates:
        # Return the longest candidate as it is likely to be the title
        title = max(candidates, key=len)
        # Clean title length
        if len(title) > 120:
            title = title[:117] + "..."
        return title
        
    return ""
