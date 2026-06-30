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

    # Chats table (with summary field for conversation summarization)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            summary TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Add total_pages column to documents if upgrading
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN total_pages INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add summary column if upgrading from an older schema (safe to run on fresh DB too)
    try:
        cursor.execute("ALTER TABLE chats ADD COLUMN summary TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            sources TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ── Chat helpers ──


def create_chat(chat_id, user_id, title="New Chat"):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO chats (id, user_id, title, summary, created_at, updated_at) VALUES (?, ?, ?, '', ?, ?)",
        (chat_id, user_id, title, now, now)
    )
    conn.commit()
    conn.close()


def get_chats_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, title, summary, created_at, updated_at FROM chats WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": r[0],
        "user_id": r[1],
        "title": r[2],
        "summary": r[3] or "",
        "created_at": r[4],
        "updated_at": r[5]
    } for r in rows]


def get_chat_by_id(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, title, summary, created_at, updated_at FROM chats WHERE id = ?",
        (chat_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "user_id": row[1],
            "title": row[2],
            "summary": row[3] if len(row) > 3 else "",
            "created_at": row[4],
            "updated_at": row[5]
        }
    return None


def update_chat_title(chat_id, title):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "UPDATE chats SET title = ?, updated_at = ? WHERE id = ?",
        (title, now, chat_id)
    )
    conn.commit()
    conn.close()


def update_chat_summary(chat_id, summary):
    """Update the summary field of a chat."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE chats SET summary = ? WHERE id = ?", (summary, chat_id))
    conn.commit()
    conn.close()


def get_message_count(chat_id):
    """Get the total number of messages in a chat."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM messages WHERE chat_id = ?", (chat_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def delete_chat(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    cursor.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()


def touch_chat(chat_id):
    """Update the updated_at timestamp of a chat."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id))
    conn.commit()
    conn.close()


# ── Message helpers ──


def save_message(msg_id, chat_id, role, content, sources=None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO messages (id, chat_id, role, content, sources, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (msg_id, chat_id, role, content, sources, now)
    )
    conn.commit()
    conn.close()


def get_messages_by_chat(chat_id, limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, chat_id, role, content, sources, created_at
           FROM messages WHERE chat_id = ?
           ORDER BY created_at ASC LIMIT ?""",
        (chat_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": r[0],
        "chat_id": r[1],
        "role": r[2],
        "content": r[3],
        "sources": r[4],
        "created_at": r[5]
    } for r in rows]


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
                            owner="default", category="general", tags="", total_pages=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO documents
        (document_id, user_id, filename, original_filename, upload_time,
         chunks, owner, category, tags, total_pages)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        document_id,
        user_id,
        filename,
        original_filename,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        chunks,
        owner,
        category,
        tags,
        total_pages or chunks
    ))
    conn.commit()
    conn.close()


def get_documents_by_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT document_id, user_id, filename, original_filename, upload_time,
                   chunks, owner, category, tags, total_pages
            FROM documents
            WHERE user_id = ?
            ORDER BY upload_time DESC
        """, (user_id,))
    except sqlite3.OperationalError:
        # Fallback if total_pages column doesn't exist yet
        cursor.execute("""
            SELECT document_id, user_id, filename, original_filename, upload_time,
                   chunks, owner, category, tags, chunks as total_pages
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


# ── Stats helpers ──


def get_document_stats(user_id):
    """Get total documents and total pages for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Use MAX(total_pages, chunks) so docs with total_pages=0 (from migration) still show chunk count
        cursor.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(CASE WHEN total_pages > 0 THEN total_pages ELSE chunks END), 0)
               FROM documents WHERE user_id = ?""",
            (user_id,)
        )
    except sqlite3.OperationalError:
        # Fallback if total_pages doesn't exist
        cursor.execute(
            "SELECT COUNT(*), COALESCE(SUM(chunks), 0) FROM documents WHERE user_id = ?",
            (user_id,)
        )
    row = cursor.fetchone()
    conn.close()
    return {"total_documents": row[0], "total_pages": row[1]}


def get_chat_stats(user_id):
    """Get total chats and total questions (user messages) for a user."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM chats WHERE user_id = ?",
        (user_id,)
    )
    total_chats = cursor.fetchone()[0]
    # Use a subquery for clarity — counts only user-role messages belonging to this user's chats
    cursor.execute(
        """SELECT COUNT(*) FROM messages
           WHERE role = 'user'
           AND chat_id IN (SELECT id FROM chats WHERE user_id = ?)""",
        (user_id,)
    )
    total_questions = cursor.fetchone()[0]
    conn.close()
    return {"total_chats": total_chats, "total_questions": total_questions}


def get_recent_chats(user_id, limit=4):
    """Get recent chats with their first user message for the dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT c.id, c.title, c.created_at, c.updated_at,
                  (SELECT m2.content FROM messages m2
                   WHERE m2.chat_id = c.id AND m2.role = 'user'
                   ORDER BY m2.created_at ASC LIMIT 1) as first_question
           FROM chats c
           WHERE c.user_id = ?
           ORDER BY c.updated_at DESC
           LIMIT ?""",
        (user_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{
        "id": r[0],
        "title": r[1],
        "created_at": r[2],
        "updated_at": r[3],
        "first_question": r[4] or r[1]
    } for r in rows]


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")