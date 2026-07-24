import os
import google.generativeai as genai
from dotenv import load_dotenv
from prompts import (
    SYSTEM_PROMPT_SUMMARIZE,
    EXECUTIVE_SUMMARY_PROMPT,
    STRUCTURED_ANALYSIS_PROMPT,
    KEY_CONCEPTS_PROMPT,
    CHAT_SYSTEM_PROMPT,
    GENERAL_CHAT_SYSTEM_PROMPT
)

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

def configure_sdk():
    """Configures the Google Generative AI SDK with the key from environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError("GEMINI_API_KEY is not set or is still the placeholder. Please update it in the .env file.")
    genai.configure(api_key=api_key)

def get_gemini_model(model_name="gemini-3.5-flash", system_instruction=None):
    """Initializes and returns a Gemini model instance."""
    configure_sdk()
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction
    )

def generate_summary(paper_text: str, summary_type: str = "executive") -> str:
    """
    Generates a structured summary of the research paper text.
    
    Args:
        paper_text (str): Full text of the paper.
        summary_type (str): Type of summary to generate ('executive', 'structured', 'concepts').
        
    Returns:
        str: Generated Markdown summary.
    """
    if not paper_text or len(paper_text.strip()) == 0:
        return "No text context found in the PDF. It might be scanned or empty."
        
    try:
        # Choose appropriate prompt template
        if summary_type == "executive":
            prompt = EXECUTIVE_SUMMARY_PROMPT
        elif summary_type == "structured":
            prompt = STRUCTURED_ANALYSIS_PROMPT
        elif summary_type == "concepts":
            prompt = KEY_CONCEPTS_PROMPT
        else:
            prompt = EXECUTIVE_SUMMARY_PROMPT
            
        model = get_gemini_model(system_instruction=SYSTEM_PROMPT_SUMMARIZE)
        
        user_message = f"""You are analyzing a research paper.

INSTRUCTIONS:
You must perform a detailed, comprehensive analysis of the entire paper text provided below. Extract concrete details, design methodologies, data parameters, and quantitative outcomes from the main body sections (Introduction, Methodology, Design, Results, and Discussion). Do NOT rely solely on the Abstract or conclusion/conflict sections.

TASK:
{prompt}

RESEARCH PAPER TEXT:
{paper_text}

REMINDER:
Generate a thorough, complete response matching the structure requested in the TASK. Make sure you extract actual numerical values, formulas, and dataset details from the text.
"""
        
        response = model.generate_content(
            contents=user_message,
            generation_config={
                "temperature": 0.25,
                "top_p": 0.95,
                "max_output_tokens": 8192,
            }
        )
        
        return response.text
        
    except Exception as e:
        return f"Error during summary generation: {str(e)}"

def chat_with_paper(chat_history: list, paper_text: str) -> str:
    """
    Sends the user question along with chat history and paper context to Gemini.
    
    Args:
        chat_history (list): List of dicts with keys 'role' ('user' or 'assistant') and 'content' (str).
        paper_text (str): Full text context of the paper.
        
    Returns:
        str: Assistant's response.
    """
    if not paper_text:
        return "No paper context available to answer questions."
        
    try:
        # Construct the context-grounded system instruction
        system_instruction = f"{CHAT_SYSTEM_PROMPT}\n\n=== RESEARCH PAPER CONTEXT ===\n{paper_text}\n============================="
        
        model = get_gemini_model(system_instruction=system_instruction)
        
        # Translate app chat history to Gemini's expected SDK format
        gemini_history = []
        for msg in chat_history[:-1]:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({
                "role": role,
                "parts": [msg["content"]]
            })
            
        chat = model.start_chat(history=gemini_history)
        
        # Send the latest user message
        latest_message = chat_history[-1]["content"]
        response = chat.send_message(
            latest_message,
            generation_config={
                "temperature": 0.3,
                "top_p": 0.95,
                "max_output_tokens": 1500,
            }
        )
        
        return response.text
        
    except Exception as e:
        return f"Error in chat processing: {str(e)}"

def chat_general(chat_history: list) -> str:
    """
    Sends the user question along with chat history to Gemini, without any paper context.
    """
    try:
        system_instruction = GENERAL_CHAT_SYSTEM_PROMPT
        model = get_gemini_model(system_instruction=system_instruction)
        
        gemini_history = []
        for msg in chat_history[:-1]:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({
                "role": role,
                "parts": [msg["content"]]
            })
            
        chat = model.start_chat(history=gemini_history)
        latest_message = chat_history[-1]["content"]
        response = chat.send_message(
            latest_message,
            generation_config={
                "temperature": 0.5,
                "top_p": 0.95,
                "max_output_tokens": 1500,
            }
        )
        
        return response.text
        
    except Exception as e:
        return f"Error in general chat: {str(e)}"
