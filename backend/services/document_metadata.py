from database import get_connection
from datetime import datetime


def save_document_metadata(
    document_id,
    filename,
    chunks,
    owner="default",
    category="general",
    tags=""
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO documents
    (
        document_id,
        filename,
        upload_time,
        chunks,
        owner,
        category,
        tags
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (
        document_id,
        filename,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        chunks,
        owner,
        category,
        tags
    ))

    conn.commit()
    conn.close()