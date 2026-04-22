# app/utils/qr_utils.py
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional

# Configuration
QR_SECRET = os.getenv("SECRET_KEY")  # Reusing your existing secret key
if not QR_SECRET:
    raise ValueError("SECRET_KEY environment variable is required for QR functionality")

QR_ALGORITHM = "HS256"
DEFAULT_QR_EXPIRY_HOURS = 24


def generate_customer_qr_token(customer_id: str, expiry_hours: int = DEFAULT_QR_EXPIRY_HOURS) -> str:
    """
    Generate a signed JWT containing the customer ID for QR code usage.

    Args:
        customer_id: The customer's SK (e.g., "CUST-0042")
        expiry_hours: Token validity period in hours (default 24)

    Returns:
        str: JWT token string
    """
    payload = {
        "sub": customer_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=expiry_hours),
        "type": "customer_qr"
    }
    return jwt.encode(payload, QR_SECRET, algorithm=QR_ALGORITHM)


def verify_customer_qr_token(token: str) -> Optional[str]:
    """
    Verify a QR JWT and return the customer ID if valid.

    Args:
        token: JWT string from QR scan

    Returns:
        Optional[str]: customer_id if token is valid and not expired, else None
    """
    try:
        payload = jwt.decode(token, QR_SECRET, algorithms=[QR_ALGORITHM])
        if payload.get("type") != "customer_qr":
            return None
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None