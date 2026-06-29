from langchain_groq import ChatGroq
from config import Config


def get_groq_llm(model="llama-3.3-70b-versatile", temperature=0.3, streaming=True):
    """Create and return a Groq LLM instance via LangChain."""
    return ChatGroq(
        model=model,
        temperature=temperature,
        streaming=streaming,
        api_key=Config.GROQ_API_KEY,
    )


def get_groq_llm_non_streaming(model="llama-3.3-70b-versatile", temperature=0.3):
    """Create a non-streaming Groq LLM (for question rewriting)."""
    return ChatGroq(
        model=model,
        temperature=temperature,
        streaming=False,
        api_key=Config.GROQ_API_KEY,
    )
