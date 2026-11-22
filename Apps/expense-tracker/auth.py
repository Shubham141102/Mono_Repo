"""Sign-up / login logic. Passwords are hashed with bcrypt, never stored as plain text."""
import re

import bcrypt

import db

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def signup(name, email, password, confirm, invite_code):
    """Returns (ok, message)."""
    name, email = name.strip(), email.strip().lower()
    required_code = db._secret("INVITE_CODE")
    max_users = int(db._secret("MAX_USERS", 10))

    if required_code and invite_code.strip() != required_code:
        return False, "Invalid invite code."
    if not name or not EMAIL_RE.match(email):
        return False, "Enter your name and a valid email."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password.encode("utf-8")) > 72:
        return False, "Password is too long (max 72 bytes)."
    if password != confirm:
        return False, "Passwords don't match."
    if db.get_user_by_email(email):
        return False, "An account with this email already exists."
    n = db.count_users()
    if n >= max_users:
        return False, f"User limit reached ({max_users}). Ask the admin."

    role = "admin" if n == 0 else "user"  # first account becomes admin
    db.create_user(name, email, hash_password(password), role)
    return True, "Account created! You can log in now." + (" (You are the admin.)" if role == "admin" else "")


def login(email, password):
    """Returns (user_dict | None, message)."""
    user = db.get_user_by_email(email.strip().lower())
    if not user or not check_password(password, user["password_hash"]):
        return None, "Invalid email or password."
    if not user["is_active"]:
        return None, "This account is deactivated. Contact the admin."
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]}, ""
