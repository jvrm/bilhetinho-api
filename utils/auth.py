"""
Authentication utilities for JWT token generation and validation
Implements secure token-based authentication with expiration
"""
import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict


# Secret key for JWT - MUST be set in environment variables for production
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8  # Tokens expire after 8 hours


def create_admin_token(admin_id: str, establishment_id: str) -> str:
    """
    Create a JWT token for an authenticated admin user

    Args:
        admin_id: UUID of the admin user
        establishment_id: UUID of the admin's establishment

    Returns:
        Encoded JWT token string

    Token includes:
        - admin_id: For user identification
        - establishment_id: For multi-tenant security
        - exp: Expiration timestamp (8 hours from now)
        - iat: Issued at timestamp
        - type: Token type identifier
    """
    payload = {
        "admin_id": admin_id,
        "establishment_id": establishment_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
        "type": "admin"
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def create_master_token() -> str:
    """
    Create a JWT token for the master account

    Returns:
        Encoded JWT token string

    Token includes:
        - exp: Expiration timestamp (8 hours from now)
        - iat: Issued at timestamp
        - type: Token type identifier
    """
    payload = {
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow(),
        "type": "master"
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def verify_admin_token(token: str) -> Optional[Dict[str, str]]:
    """
    Verify and decode an admin JWT token

    Args:
        token: JWT token string to verify

    Returns:
        Dict with admin_id and establishment_id if valid, None if invalid

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Verify token type
        if payload.get("type") != "admin":
            return None

        return {
            "admin_id": payload.get("admin_id"),
            "establishment_id": payload.get("establishment_id")
        }
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")


def verify_master_token(token: str) -> bool:
    """
    Verify a master JWT token

    Args:
        token: JWT token string to verify

    Returns:
        True if valid master token, False otherwise

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        # Verify token type
        return payload.get("type") == "master"
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except jwt.InvalidTokenError:
        raise Exception("Invalid token")
