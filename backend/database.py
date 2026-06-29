import sqlite3
from datetime import datetime

DB_NAME = "app.db"


def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Documents table (with user_id foreign key)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            filename TEXT NOT NULL,
            original_filename TEXT,
            upload_time TEXT NOT NULL,
            chunks INTEGER NOT NULL DEFAULT 0,
            owner TEXT,
            category TEXT,
            tags TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Chunks table (with user_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            page_number INTEGER,
            filename TEXT,
            owner TEXT,
            category TEXT,
            FOREIGN KEY (document_id) REFERENCES documents(document_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ── User helpers ──


def get_user_by_email(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "password_hash": row[3],
            "created_at": row[4]
        }
    return None


def get_user_by_id(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password_hash, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "password_hash": row[3],
            "created_at": row[4]
        }
    return None


def create_user(user_id, name, email, password_hash, created_at):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, email, password_hash, created_at)
    )
    conn.commit()
    conn.close()


# ── Document helpers ──


def save_document_metadata(document_id, user_id, filename, original_filename, chunks,
                            owner="default", category="general", tags=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents
        (document_id, user_id, filename, original_filename, upload_time,
         chunks, owner, category, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        document_id,
        user_id,
        filename,
        original_filename,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        chunks,
        owner,
        category,
        tags
    ))
    conn.commit()
    conn.close()


def get_documents_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT document_id, user_id, filename, original_filename, upload_time,
               chunks, owner, category, tags
        FROM documents
        WHERE user_id = ?
        ORDER BY upload_time DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def delete_document_meta(document_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    cursor.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
    conn.commit()
    conn.close()


# ── Chunk helpers ──


def save_chunks(chunk_records):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executemany("""
        INSERT OR REPLACE INTO chunks (
            chunk_id, document_id, user_id, chunk_text,
            page_number, filename, owner, category
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, chunk_records)
    conn.commit()
    conn.close()


def get_chunks(document_id=None, category=None, owner=None, user_id=None):
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

    if user_id:
        query += " AND user_id=?"
        params.append(user_id)
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