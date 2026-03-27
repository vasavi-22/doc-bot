from pypdf import PdfReader

def load_pdf(file_path):
    reader = PdfReader(file_path)
    
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    return split_text(text)


def split_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap  # 🔥 overlap

    return chunks