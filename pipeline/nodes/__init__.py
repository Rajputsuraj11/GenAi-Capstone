import os
import time
import threading
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Thread-local storage for Groq clients (each thread gets its own client)
_thread_local = threading.local()

# Rate limiting using thread-safe lock
_LAST_CALL_TIME = 0
_rate_limit_lock = threading.Lock()
MIN_DELAY_SECONDS = 3  # Wait 3 seconds between calls (conservative)


def _get_groq_client():
    """Get or create a thread-local Groq client."""
    if not hasattr(_thread_local, 'client'):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None
        _thread_local.client = Groq(api_key=api_key)
    return _thread_local.client


def call_groq(prompt: str, max_tokens: int = 1024) -> str:
    """Wrapper for Groq API calls with thread-safe rate limiting and error handling."""
    global _LAST_CALL_TIME

    client = _get_groq_client()
    if client is None:
        return "ERROR: GROQ_API_KEY not configured"

    # Thread-safe rate limiting
    with _rate_limit_lock:
        elapsed = time.time() - _LAST_CALL_TIME
        if elapsed < MIN_DELAY_SECONDS:
            wait_time = MIN_DELAY_SECONDS - elapsed
            time.sleep(wait_time)
        _LAST_CALL_TIME = time.time()

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
        return response.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"ERROR: 429 Rate limit exceeded. Free tier allows 20 requests/minute. Wait 60 seconds and try again with a smaller PDF."
        return f"ERROR: {error_msg}"
