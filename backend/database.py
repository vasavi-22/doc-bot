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

    conn.commit()
    conn.close()