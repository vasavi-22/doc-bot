import sqlite3

DB_NAME = "documents.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            upload_time TEXT NOT NULL,
            chunks INTEGER NOT NULL,
            owner TEXT,
            category TEXT,
            tags TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            page_number INTEGER,
            filename TEXT,
            owner TEXT,
            category TEXT,

            FOREIGN KEY(document_id)
            REFERENCES documents(document_id)
        )
    """)

    conn.commit()
    conn.close()

def save_chunks(chunk_records):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR REPLACE INTO chunks (
            chunk_id,
            document_id,
            chunk_text,
            page_number,
            filename,
            owner,
            category
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, chunk_records)

    conn.commit()
    conn.close()

def get_chunks(
    document_id=None,
    category=None,
    owner=None
):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            chunk_id,
            document_id,
            chunk_text,
            page_number,
            filename,
            owner,
            category
        FROM chunks
        WHERE 1=1
    """

    params = []

    if document_id:
        query += " AND document_id=?"
        params.append(document_id)

    if category:
        query += " AND category=?"
        params.append(category)

    if owner:
        query += " AND owner=?"
        params.append(owner)

    cursor.execute(query, params)

    rows = cursor.fetchall()

    conn.close()

    return rows


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")