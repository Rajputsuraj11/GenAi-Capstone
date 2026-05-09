import os
import time
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

# Rate limiting: Free tier = 15 RPM (1 request per 4 seconds)
LAST_CALL_TIME = 0
MIN_DELAY_SECONDS = 4  # Wait 4 seconds between calls


def call_gemini(prompt: str, max_tokens: int = 1024) -> str:
    """Wrapper for Gemini API calls with rate limiting and error handling."""
    global LAST_CALL_TIME

    if model is None:
        return "ERROR: API key not configured"

    # Rate limiting - wait if needed
    elapsed = time.time() - LAST_CALL_TIME
    if elapsed < MIN_DELAY_SECONDS:
        wait_time = MIN_DELAY_SECONDS - elapsed
        time.sleep(wait_time)

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.1,
            )
        )
        LAST_CALL_TIME = time.time()
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"ERROR: 429 Rate limit exceeded. Free tier allows 15 requests/minute. Wait 60 seconds and try again with a smaller PDF."
        return f"ERROR: {error_msg}"
