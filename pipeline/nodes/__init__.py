import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Configure Groq clients for different agents
def get_groq_client_pii():
    """Get Groq client for PII agent."""
    api_key = os.getenv("GROQ_API_KEY_PII")
    if not api_key:
        raise ValueError("ERROR: GROQ_API_KEY_PII not configured")
    return Groq(api_key=api_key)

def get_groq_client_confidential():
    """Get Groq client for Confidential agent."""
    api_key = os.getenv("GROQ_API_KEY_CONFIDENTIAL")
    if not api_key:
        raise ValueError("ERROR: GROQ_API_KEY_CONFIDENTIAL not configured")
    return Groq(api_key=api_key)

def get_groq_client_abusive():
    """Get Groq client for Abusive agent."""
    api_key = os.getenv("GROQ_API_KEY_ABUSIVE")
    if not api_key:
        raise ValueError("ERROR: GROQ_API_KEY_ABUSIVE not configured")
    return Groq(api_key=api_key)

def call_groq_pii(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Wrapper function for PII agent Groq API calls.
    """
    client = get_groq_client_pii()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a PII detection expert. Analyze the provided text and respond with only the requested information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"ERROR: 429 Rate limit exceeded on PII agent. Wait 60 seconds and try again."
        return f"ERROR: {error_msg}"

def call_groq_confidential(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Wrapper function for Confidential agent Groq API calls.
    """
    client = get_groq_client_confidential()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a confidential information detection expert. Analyze the provided text and respond with only the requested information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"ERROR: 429 Rate limit exceeded on Confidential agent. Wait 60 seconds and try again."
        return f"ERROR: {error_msg}"

def call_groq_abusive(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Wrapper function for Abusive agent Groq API calls.
    """
    client = get_groq_client_abusive()
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an abusive content detection expert. Analyze the provided text and respond with only the requested information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return f"ERROR: 429 Rate limit exceeded on Abusive agent. Wait 60 seconds and try again."
        return f"ERROR: {error_msg}"
