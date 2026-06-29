def build_chunk_metadata(
    chunks,
    document_id,
    filename,
    owner,
    category,
    user_id=None
):

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

        metadata.append(meta)

    return metadata