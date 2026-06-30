def build_chunk_metadata(
    chunks,
    document_id,
    filename,
    owner,
    category,
    user_id=None,
    tags="",
    allowed_roles=None
):

    # Parse tags into a list for Pinecone metadata filtering
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    # Default allowed_roles: everyone
    if allowed_roles is None:
        allowed_roles_list = ["admin", "employee"]
    elif isinstance(allowed_roles, str):
        import json
        try:
            allowed_roles_list = json.loads(allowed_roles)
        except (json.JSONDecodeError, TypeError):
            allowed_roles_list = ["admin", "employee"]
    else:
        allowed_roles_list = allowed_roles

    metadata = []

    for chunk in chunks:

        meta = {
            "document_id": document_id,
            "filename": filename,
            "page_number": chunk["page_number"],
            "owner": owner,
            "category": category,
            "allowed_roles": allowed_roles_list
        }

        if user_id:
            meta["user_id"] = user_id

        if tag_list:
            meta["tags"] = tag_list

        metadata.append(meta)

    return metadata