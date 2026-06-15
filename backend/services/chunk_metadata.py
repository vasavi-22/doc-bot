def build_chunk_metadata(
    chunks,
    document_id,
    filename,
    owner,
    category
):

    metadata = []

    for chunk in chunks:

        metadata.append({
            "document_id": document_id,
            "filename": filename,
            "page_number": chunk["page_number"],
            "owner": owner,
            "category": category
        })

    return metadata