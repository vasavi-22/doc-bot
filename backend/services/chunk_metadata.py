def build_chunk_metadata(
    chunks,
    document_id,
    filename,
    owner,
    category,
    user_id=None,
    tags=""
):

    # Parse tags into a list for Pinecone metadata filtering
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    metadata = []

    for chunk in chunks:

        meta = {
            "document_id": document_id,
            "filename": filename,
            "page_number": chunk["page_number"],
            "owner": owner,
            "category": category
        }

        if user_id:
            meta["user_id"] = user_id

        if tag_list:
            meta["tags"] = tag_list

        metadata.append(meta)

    return metadata