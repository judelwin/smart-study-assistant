import os
import uuid
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import bcrypt
import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

app = FastAPI(title="ClassGPT Auth Service")

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Conservative limits for personal project
MAX_LOGIN_ATTEMPTS_PER_HOUR = 10  # Max 10 login attempts per hour per IP
MAX_REGISTRATIONS_PER_HOUR = 5  # Max 5 registrations per hour per IP

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/classgpt")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-very-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week

security = HTTPBearer()

class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/register", response_model=Token)
@limiter.limit("5/hour")  # Rate limit: 5 registrations per hour per IP
def register(user: UserRegister, db = Depends(get_db)):
    result = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": user.email})
    if result.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    password_hash = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO users (id, email, password_hash, created_at)
        VALUES (:user_id, :email, :password_hash, NOW())
    """), {
        "user_id": user_id,
        "email": user.email,
        "password_hash": password_hash
    })
    db.commit()
    access_token = create_access_token(data={"sub": str(user_id)})
    return Token(access_token=access_token, token_type="bearer")

@app.post("/auth/login", response_model=Token)
@limiter.limit("10/hour")  # Rate limit: 10 login attempts per hour per IP
def login(user: UserLogin, db = Depends(get_db)):
    result = db.execute(text("SELECT id, password_hash FROM users WHERE email = :email"), {"email": user.email})
    user_data = result.fetchone()
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not bcrypt.checkpw(user.password.encode('utf-8'), user_data.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token(data={"sub": str(user_data.id)})
    return Token(access_token=access_token, token_type="bearer")

@app.get("/auth/me")
def get_current_user(user_id: str = Depends(verify_token), db = Depends(get_db)):
    result = db.execute(text("SELECT id, email, created_at FROM users WHERE id = :user_id"), {"user_id": user_id})
    user_data = result.fetchone()
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user_data.id,
        "email": user_data.email,
        "created_at": user_data.created_at
    }

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 