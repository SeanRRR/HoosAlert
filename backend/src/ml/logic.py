# logic.py - Gemini AI integration for severity scoring
import google.generativeai as genai

# Configure Gemini (add your API key)
genai.configure(api_key="YOUR_GEMINI_API_KEY")

def score_incident(text: str) -> dict:
    """
    Use Gemini to score incident severity.
    Returns JSON with severity (1-5) and details.
    """
    prompt = f"Analyze this incident report and output only JSON: {{'severity': int, 'type': str}}. Text: {text}"
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    # Parse response (simplified)
    return {"severity": 3, "type": "unknown"}  # Placeholder