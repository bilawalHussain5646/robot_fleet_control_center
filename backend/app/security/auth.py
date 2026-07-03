from datetime import datetime, timedelta
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db
from app.models.models import User
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
ROLE_PERMS = {"admin":{"*"},"operator":{"robots:read","commands:send","tasks:write","alerts:read","maintenance:read","analytics:read"},"technician":{"robots:read","alerts:read","alerts:write","maintenance:read","maintenance:write","commands:send","analytics:read"},"viewer":{"robots:read","alerts:read","maintenance:read","analytics:read"}}
def hash_password(p: str) -> str: return pwd_context.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd_context.verify(p, h)
def create_token(sub: str, minutes: int, typ: str = "access") -> str:
    return jwt.encode({"sub": sub, "type": typ, "jti": str(uuid.uuid4()), "exp": datetime.utcnow()+timedelta(minutes=minutes)}, settings.jwt_secret, algorithm="HS256")
def current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try: payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.get(User, payload.get("sub"))
    if not user or not user.is_active: raise HTTPException(status_code=401, detail="Inactive user")
    return user
def require_perm(permission: str):
    def dep(user: User = Depends(current_user)) -> User:
        perms = ROLE_PERMS.get(user.role.value, set())
        if "*" not in perms and permission not in perms: raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dep
