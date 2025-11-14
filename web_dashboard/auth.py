"""
Authentication System for Web Dashboard
Handles user authentication, JWT tokens, and session management
"""
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("WEB_SECRET_KEY", "your-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Security
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            return None
            
        return {"username": username}
        
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    user = verify_token(token)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

class UserManager:
    """Manage users in database"""
    
    def __init__(self, db):
        self.db = db
        self._ensure_users_table()
    
    def _ensure_users_table(self):
        """Create users table if it doesn't exist"""
        try:
            self.db.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            self.db.conn.commit()
        except Exception as e:
            print(f"Error creating users table: {e}")
    
    def create_user(self, username: str, password: str) -> bool:
        """Create a new user"""
        try:
            hashed_password = get_password_hash(password)
            
            self.db.cursor.execute(
                'INSERT INTO users (username, hashed_password) VALUES (?, ?)',
                (username, hashed_password)
            )
            self.db.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate a user"""
        try:
            self.db.cursor.execute(
                'SELECT id, username, hashed_password, is_active FROM users WHERE username = ?',
                (username,)
            )
            user = self.db.cursor.fetchone()
            
            if not user:
                return None
            
            user_id, username, hashed_password, is_active = user
            
            if not is_active:
                return None
            
            if not verify_password(password, hashed_password):
                return None
            
            # Update last login
            self.db.cursor.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.now(), user_id)
            )
            self.db.conn.commit()
            
            return {"id": user_id, "username": username}
            
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    def user_exists(self, username: str) -> bool:
        """Check if a user exists"""
        try:
            self.db.cursor.execute(
                'SELECT COUNT(*) FROM users WHERE username = ?',
                (username,)
            )
            count = self.db.cursor.fetchone()[0]
            return count > 0
            
        except Exception as e:
            print(f"Error checking user: {e}")
            return False
    
    def get_user_count(self) -> int:
        """Get total number of users"""
        try:
            self.db.cursor.execute('SELECT COUNT(*) FROM users')
            return self.db.cursor.fetchone()[0]
        except:
            return 0
