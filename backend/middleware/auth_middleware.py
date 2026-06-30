from functools import wraps
from flask import request, jsonify, g
from services.auth_service import decode_jwt, get_current_user


def jwt_required(f):
    """Decorator that requires a valid JWT token.

    Checks the Authorization header first, then falls back to a `token`
    query parameter (useful for direct URL access like viewing documents
    in a new tab).

    On success, sets g.user_id with the authenticated user's ID,
    and g.user_role with the user's role.
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

        # Also load user role for RBAC
        user = get_current_user(g.user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        g.user_role = user.get("role", "employee")

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


def require_role(role):
    """Decorator that requires the authenticated user to have a specific role.

    Must be used AFTER @jwt_required.

    Example:
        @jwt_required
        @require_role("admin")
        def admin_only_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = getattr(g, "user_role", None)
            if user_role != role:
                return jsonify({"error": f"Forbidden: {role} role required"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_any_role(*roles):
    """Decorator that requires the authenticated user to have at least one of the specified roles.

    Must be used AFTER @jwt_required.

    Example:
        @jwt_required
        @require_any_role("admin", "manager")
        def manager_or_admin_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_role = getattr(g, "user_role", None)
            if user_role not in roles:
                return jsonify({"error": f"Forbidden: one of {roles} roles required"}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
