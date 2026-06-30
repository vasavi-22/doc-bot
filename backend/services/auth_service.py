import uuid
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from config import Config
from database import get_user_by_email, get_user_by_id, create_user


def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, password_hash):
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_jwt(user_id):
    """Create a JWT token for the given user_id."""
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


def decode_jwt(token):
    """Decode and verify a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def register_user(name, email, password):
    """Register a new user. Returns (success, result_dict).

    New users are created with the default 'employee' role.
    """
    # Validate inputs
    if not name or not name.strip():
        return False, {"error": "Name is required"}

    if not email or not email.strip():
        return False, {"error": "Email is required"}

    if not password or len(password) < 6:
        return False, {"error": "Password must be at least 6 characters"}

    # Check if email already exists
    existing = get_user_by_email(email.strip().lower())
    if existing:
        return False, {"error": "Email already registered"}

    # Create user with default 'employee' role
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    password_hash = hash_password(password)

    create_user(user_id, name.strip(), email.strip().lower(), password_hash, now, role="employee")

    token = create_jwt(user_id)

    return True, {
        "token": token,
        "user": {
            "id": user_id,
            "name": name.strip(),
            "email": email.strip().lower(),
            "role": "employee"
        }
    }


def login_user(email, password):
    """Login a user. Returns (success, result_dict)."""
    if not email or not password:
        return False, {"error": "Email and password are required"}

    user = get_user_by_email(email.strip().lower())
    if not user:
        return False, {"error": "Invalid email or password"}

    if not verify_password(password, user["password_hash"]):
        return False, {"error": "Invalid email or password"}

    token = create_jwt(user["id"])

    return True, {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


def get_current_user(user_id):
    """Get user info by ID."""
    user = get_user_by_id(user_id)
    if not user:
        return None
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"]
    }
