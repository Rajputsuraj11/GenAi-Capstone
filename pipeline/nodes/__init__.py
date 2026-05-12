import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configure Groq client
def get_groq_client():
    """Get Groq client with API key from environment."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("ERROR: GROQ_API_KEY not configured")
    return Groq(api_key=api_key)

def call_groq(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Wrapper function for Groq API calls.
    
    Args:
        prompt: The prompt to send to Groq
        model: Model to use (default: llama-3.3-70b-versatile)
    
    Returns:
        Response text from Groq
    """
    client = get_groq_client()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a compliance expert. Analyze the provided text and respond with only the requested information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"ERROR: 429 Rate limit exceeded. Free tier allows 20 requests/minute. Wait 60 seconds and try again with a smaller PDF."
        return f"ERROR: {error_msg}"
