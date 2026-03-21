import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import HTTPException
from backend.src.auth import verify_token

def test_verify_token_valid():
    # Simulate a valid token
    token = "valid_token"
    result = verify_token(token)
    assert result == {"user": "authenticated"}

def test_verify_token_invalid():
    # Simulate an invalid token
    try:
        verify_token(None)
    except HTTPException as e:
        assert e.status_code == 401
        assert e.detail == "Invalid token"