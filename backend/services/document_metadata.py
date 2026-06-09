from database import get_connection
from datetime import datetime


def save_document_metadata(filename, chunks):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO documents
        (filename, upload_time, chunks)
        VALUES (?, ?, ?)
    """, (
        filename,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        chunks
    ))

    conn.commit()
    conn.close()