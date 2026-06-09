from pypdf import PdfReader
from config import Config

def load_pdf(file_path):
    reader = PdfReader(file_path)
    
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    if not text.strip():
        raise Exception("No extractable text found")

    return split_text(text)


def split_text(text, chunk_size=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap  # 🔥 overlap

    return chunks