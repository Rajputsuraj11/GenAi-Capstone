import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

# Rate limiting: Groq free tier = 20 requests/minute for llama3-8b
LAST_CALL_TIME = 0
MIN_DELAY_SECONDS = 3  # Wait 3 seconds between calls (conservative)


def call_groq(prompt: str, max_tokens: int = 1024) -> str:
    """Wrapper for Groq API calls with rate limiting and error handling."""
    global LAST_CALL_TIME

    if client is None:
        return "ERROR: GROQ_API_KEY not configured"

    # Rate limiting - wait if needed
    elapsed = time.time() - LAST_CALL_TIME
    if elapsed < MIN_DELAY_SECONDS:
        wait_time = MIN_DELAY_SECONDS - elapsed
        time.sleep(wait_time)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a compliance analysis AI. Respond only in valid JSON format as requested."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=max_tokens
        )
        LAST_CALL_TIME = time.time()
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"ERROR: 429 Rate limit exceeded. Free tier allows 20 requests/minute. Wait 60 seconds and try again with a smaller PDF."
        return f"ERROR: {error_msg}"
