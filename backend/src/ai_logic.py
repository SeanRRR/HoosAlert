import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def process_with_gemini(text: str):
    prompt = f"""
    You are a UVA campus safety dispatcher. Analyze this report: "{text}"
    Return ONLY a JSON object with:
    - lat (float, near 38.0356)
    - lng (float, near -78.5034)
    - type (string, e.g., 'Fire', 'Medical', 'Suspicious')
    - severity (int 1-5)
    - summary (string, max 10 words)
    """
    response = model.generate_content(prompt)
    # Clean markdown if Gemini adds it
    clean_text = response.text.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_text)