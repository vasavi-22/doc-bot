import requests
from sentence_transformers import SentenceTransformer
from services.vector_store import query_vectors

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')


def query_rag(question):
    try:
        # 🔹 Step 1: Create embedding
        q_embedding = model.encode(question).tolist()

        # 🔹 Step 2: Retrieve from Pinecone
        result = query_vectors(q_embedding, top_k=5)
        matches = result.get("matches", [])

        # 🔹 Step 3: Filter relevant chunks
        context_chunks = [
            match["metadata"]["text"]
            for match in matches
            if match["score"] > 0.6
        ]

        context = "\n\n".join(context_chunks)

        # 🔥 Step 4: Model selection
        if context.strip():
            model_name = "phi3"   # better reasoning for RAG

            prompt = f"""
You are an intelligent AI assistant.

Answer ONLY from the provided context.

If the answer is not in the context, say:
"I don't know based on the provided documents."

Format your response like ChatGPT:
- Use headings
- Use bullet points
- Use emojis where helpful
- Keep it clear and structured

Context:
{context}

Question:
{question}

Answer:
"""
        else:
            model_name = "phi"  # fast fallback

            prompt = f"""
You are a helpful AI assistant.

Answer the question clearly and in a structured way like ChatGPT.

- Use headings
- Use bullet points
- Use emojis
- Be concise but informative

Question:
{question}

Answer:
"""

        # 🔹 Step 5: Call Ollama
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )

        data = response.json()

        # 🔥 Step 6: Safe handling
        if "response" in data:
            return data["response"]
        elif "error" in data:
            return f"❌ Ollama Error: {data['error']}"
        else:
            return f"⚠️ Unexpected response: {data}"

    except Exception as e:
        return f"❌ Internal Error: {str(e)}"