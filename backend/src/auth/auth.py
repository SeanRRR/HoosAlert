# auth.py - Auth0 integration (placeholder)
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

def verify_token(token: str = Depends(security)):
    # Verify Auth0 JWT (simplified)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"user": "authenticated"}
