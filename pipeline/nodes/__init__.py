import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
    except:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
else:
    model = None


def call_gemini(prompt: str, max_tokens: int = 1024) -> str:
    """Wrapper for Gemini API calls with error handling."""
    if model is None:
        return "ERROR: API key not configured"
    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.1,
            )
        )
        return response.text
    except Exception as e:
        return f"ERROR: {str(e)}"
