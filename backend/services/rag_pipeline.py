import requests
# from sentence_transformers import SentenceTransformer
from services.vector_store import query_vectors
from config import Config
from utils.logger import logger
from services.model_loader import get_model

# model = SentenceTransformer(Config.EMBEDDING_MODEL)
# model = get_model()

GROQ_API_KEY = Config.GROQ_API_KEY
TOP_K_RESULTS = Config.TOP_K_RESULTS

def query_rag(question, document_id=None, category=None, owner=None):
    try:
        if not GROQ_API_KEY:
            return "❌ GROQ_API_KEY not set"

        # 🔹 Step 1: Embedding
        # q_embedding = model.encode(question).tolist()
        q_embedding = get_model().encode(question).tolist()

        logger.info("Querying Pinecone")
        # 🔹 Step 2: Retrieve context

        pinecone_filter = {}

        if document_id:
            pinecone_filter["document_id"] = document_id

        if category:
            pinecone_filter["category"] = category

        if owner:
            pinecone_filter["owner"] = owner

        result = query_vectors(q_embedding, top_k=TOP_K_RESULTS, filter=pinecone_filter if pinecone_filter else None)
        matches = result.get("matches", [])

        # 🔥 Filter relevant chunks
        # context_chunks = [
        #     match["metadata"]["text"]
        #     for match in matches
        #     if match.get("score", 0) > 0.75
        # ]

        # context = "\n\n".join(context_chunks)[:1500]

        context_chunks = []
        sources = []

        for match in matches:
            if match.get("score", 0) > 0.75:
                metadata = match["metadata"]

                filename = metadata.get("filename", "Unknown")
                page_number = metadata.get("page_number", "N/A")
                text = metadata.get("text", "")

                context_chunks.append(
                f"""
        Document: {filename}
        Page: {page_number}

        {text}
        """
                )

                sources.append(
                f"{filename} (Page {page_number})"
                )

        context = "\n\n".join(context_chunks)[:2000]
        unique_sources = list(set(sources))

        # 🔥 Prompt logic
        if context.strip():
            system_prompt = """
You are an AI assistant specialized in document question answering.

Rules:
1. Answer ONLY from the provided context.
2. If information is missing, respond:
   "I don't know based on the provided documents."
3. Do not hallucinate.
4. Use headings and bullet points.
5. Be concise and accurate.
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
            # return data["choices"][0]["message"]["content"]

            answer = data["choices"][0]["message"]["content"]
            if unique_sources:
                answer += "\n\n---\n**Sources:**\n"

                for source in unique_sources:
                    answer += f"- {source}\n"
            return answer

        elif "error" in data:
            return f"❌ Groq API Error: {data['error']['message']}"
        else:
            return f"⚠️ Unexpected response: {data}"

    except Exception as e:
        return f"❌ Error: {str(e)}"