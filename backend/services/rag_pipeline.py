import requests
from sentence_transformers import SentenceTransformer
from services.vector_store import query_vectors
import os
from config import Config
from utils.logger import logger
from services.model_loader import get_model

# model = SentenceTransformer(Config.EMBEDDING_MODEL)
model = get_model()

GROQ_API_KEY = Config.GROQ_API_KEY
TOP_K_RESULTS = Config.TOP_K_RESULTS

def query_rag(question):
    try:
        if not GROQ_API_KEY:
            return "❌ GROQ_API_KEY not set"

        # 🔹 Step 1: Embedding
        # q_embedding = model.encode(question).tolist()
        q_embedding = get_model().encode(question).tolist()

        logger.info("Querying Pinecone")
        # 🔹 Step 2: Retrieve context
        result = query_vectors(q_embedding, top_k=TOP_K_RESULTS)
        matches = result.get("matches", [])

        # 🔥 Filter relevant chunks
        context_chunks = [
            match["metadata"]["text"]
            for match in matches
            if match.get("score", 0) > 0.75
        ]

        context = "\n\n".join(context_chunks)[:1500]

        # 🔥 Prompt logic
        if context.strip():
            system_prompt = """You are an AI assistant.

Answer ONLY from the provided context.
If answer not found, say:
"I don't know based on the provided documents."

Format:
- Headings
- Bullet points
- Clear and concise
"""
            user_content = f"""
Context:
{context}

Question:
{question}
"""
        else:
            system_prompt = """You are a ChatGPT-like assistant.

Give clear, structured answers:
- Headings
- Bullet points
- Examples
- Concise
"""
            user_content = f"Question:\n{question}"

        # 🔹 Step 4: API call
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "temperature": 0.3,
                "max_tokens": 200
            },
            timeout=30
        )

        data = response.json()

        # 🔥 Safe response handling
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        elif "error" in data:
            return f"❌ Groq API Error: {data['error']['message']}"
        else:
            return f"⚠️ Unexpected response: {data}"

    except Exception as e:
        return f"❌ Error: {str(e)}"