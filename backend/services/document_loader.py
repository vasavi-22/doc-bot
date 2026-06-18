from pypdf import PdfReader
from config import Config
from utils.logger import logger

from pdf2image import convert_from_path
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Users\Lucky33\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
)

def extract_text_with_ocr(file_path):
    all_chunks = []

    images = convert_from_path(file_path, poppler_path=r"C:\poppler\poppler-26.02.0\Library\bin")

    for page_num, image in enumerate(images, start=1):

        logger.info(
            f"Running OCR on page {page_num}"
        )

        text = pytesseract.image_to_string(image)

        if text.strip():

            chunks = split_text(text)

            for chunk in chunks:
                all_chunks.append({
                    "text": chunk,
                    "page_number": page_num
                })

    return all_chunks

def load_pdf(file_path):
    reader = PdfReader(file_path)

    all_chunks = []
    
    text = ""
    
    for page_num, page in enumerate(reader.pages, start=1):

        text = page.extract_text() or ""

        if text.strip():

            chunks = split_text(text)

            for chunk in chunks:
                all_chunks.append({
                    "text": chunk,
                    "page_number": page_num
                })

    if not all_chunks:
        logger.info(
            "No extractable text found. Falling back to OCR."
        )
        all_chunks = extract_text_with_ocr(file_path)
        if not all_chunks:
            raise Exception(
                "No text could be extracted from this PDF."
            )

    return all_chunks

def split_text(text, chunk_size=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap  # overlap

    return chunks