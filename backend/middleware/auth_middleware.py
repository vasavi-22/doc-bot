from functools import wraps
from flask import request, jsonify, g
from services.auth_service import decode_jwt


def jwt_required(f):
    """Decorator that requires a valid JWT token.

    Checks the Authorization header first, then falls back to a `token`
    query parameter (useful for direct URL access like viewing documents
    in a new tab).

    On success, sets g.user_id with the authenticated user's ID.
    On failure, returns 401 JSON response.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check Authorization header first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

        # Fall back to query parameter
        if not token:
            token = request.args.get("token")

        if not token:
            return jsonify({"error": "Missing or invalid authorization token"}), 401

        payload = decode_jwt(token)
        if payload is None:
            return jsonify({"error": "Invalid or expired token"}), 401

        g.user_id = payload["user_id"]
        return f(*args, **kwargs)

    return decorated


def optional_jwt(f):
    """Decorator that optionally extracts JWT if present, but doesn't require it.

    Sets g.user_id if token is valid, otherwise g.user_id is None.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        g.user_id = None

        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]
            payload = decode_jwt(token)
            if payload is not None:
                g.user_id = payload["user_id"]

        return f(*args, **kwargs)

    return decorated
