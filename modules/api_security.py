"""
API Security module for the Conference Presentation System.
Implements JWT authentication, role-based access control, and request validation.
"""

import time
import jwt
import logging
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from pydantic import BaseModel, ValidationError
from jose import JWTError

# Configure logging
logger = logging.getLogger("APISecurityModule")

# Security configuration
SECURITY_CONFIG = {
    "SECRET_KEY": os.environ.get("API_SECRET_KEY", secrets.token_hex(32)),
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": 30,
    "REFRESH_TOKEN_EXPIRE_DAYS": 7,
    "ALLOWED_CORS_ORIGINS": ["*"],  # Restrict in production
    "PASSWORD_SALT": os.environ.get("PASSWORD_SALT", secrets.token_hex(16)),
    "RATE_LIMIT_ENABLED": True,
    "RATE_LIMIT_PER_MINUTE": 60,  # Requests per minute
    "IP_WHITELIST": [],  # Empty means no whitelist
}

# User roles
ROLE_ADMIN = "admin"          # Full system access
ROLE_MODERATOR = "moderator"  # Presentation control access
ROLE_PRESENTER = "presenter"  # Limited to presenter functions
ROLE_VIEWER = "viewer"        # Read-only access

# User database (replace with actual database in production)
class UserInDB(BaseModel):
    username: str
    email: str
    hashed_password: str
    disabled: bool = False
    roles: List[str] = []

# Sample users for development
USERS_DB = {
    "admin": UserInDB(
        username="admin",
        email="admin@example.com",
        hashed_password=hashlib.sha256((f"admin123{SECURITY_CONFIG['PASSWORD_SALT']}").encode()).hexdigest(),
        roles=[ROLE_ADMIN]
    ),
    "moderator": UserInDB(
        username="moderator",
        email="moderator@example.com",
        hashed_password=hashlib.sha256((f"mod123{SECURITY_CONFIG['PASSWORD_SALT']}").encode()).hexdigest(),
        roles=[ROLE_MODERATOR]
    ),
    "presenter": UserInDB(
        username="presenter",
        email="presenter@example.com",
        hashed_password=hashlib.sha256((f"present123{SECURITY_CONFIG['PASSWORD_SALT']}").encode()).hexdigest(),
        roles=[ROLE_PRESENTER]
    ),
    "viewer": UserInDB(
        username="viewer",
        email="viewer@example.com",
        hashed_password=hashlib.sha256((f"view123{SECURITY_CONFIG['PASSWORD_SALT']}").encode()).hexdigest(),
        roles=[ROLE_VIEWER]
    ),
}

# Token models
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class User(BaseModel):
    username: str
    email: str
    disabled: Optional[bool] = None
    roles: List[str] = []

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        ROLE_ADMIN: "Full system access",
        ROLE_MODERATOR: "Presentation control access",
        ROLE_PRESENTER: "Presenter functions",
        ROLE_VIEWER: "Read-only access",
    },
)

# Rate limiting implementation
rate_limits = {}

def check_rate_limit(username: str, client_ip: str) -> bool:
    """
    Check if the user has exceeded rate limits.
    Returns True if request is allowed, False if rate limited.
    """
    if not SECURITY_CONFIG["RATE_LIMIT_ENABLED"]:
        return True
        
    # Allow IP whitelist to bypass rate limiting
    if client_ip in SECURITY_CONFIG["IP_WHITELIST"]:
        return True
    
    current_time = time.time()
    key = f"{username}:{client_ip}"
    
    if key not in rate_limits:
        rate_limits[key] = {"count": 1, "reset_time": current_time + 60}
        return True
    
    # Check if we need to reset the counter
    if current_time > rate_limits[key]["reset_time"]:
        rate_limits[key] = {"count": 1, "reset_time": current_time + 60}
        return True
    
    # Increment counter and check limit
    rate_limits[key]["count"] += 1
    if rate_limits[key]["count"] > SECURITY_CONFIG["RATE_LIMIT_PER_MINUTE"]:
        logger.warning(f"Rate limit exceeded for {key}")
        return False
    
    return True

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    salted_password = f"{plain_password}{SECURITY_CONFIG['PASSWORD_SALT']}"
    return hashlib.sha256(salted_password.encode()).hexdigest() == hashed_password

def get_user(db, username: str) -> Optional[UserInDB]:
    """Get a user from the database."""
    if username in db:
        return db[username]
    return None

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user by username and password."""
    user = get_user(USERS_DB, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=SECURITY_CONFIG["ACCESS_TOKEN_EXPIRE_MINUTES"])
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECURITY_CONFIG["SECRET_KEY"], algorithm=SECURITY_CONFIG["ALGORITHM"])
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token with longer expiry."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=SECURITY_CONFIG["REFRESH_TOKEN_EXPIRE_DAYS"])
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECURITY_CONFIG["SECRET_KEY"], algorithm=SECURITY_CONFIG["ALGORITHM"])
    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes, 
    token: str = Depends(oauth2_scheme)
) -> User:
    """Validate the access token and return the current user."""
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        payload = jwt.decode(
            token, 
            SECURITY_CONFIG["SECRET_KEY"], 
            algorithms=[SECURITY_CONFIG["ALGORITHM"]]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(scopes=token_scopes, username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(USERS_DB, username=token_data.username)
    if user is None:
        raise credentials_exception
    
    # Check if token has the required scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required: {scope}",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return User(
        username=user.username,
        email=user.email,
        disabled=user.disabled,
        roles=user.roles
    )

async def get_current_active_user(
    current_user: User = Security(get_current_user, scopes=[])
) -> User:
    """Check if the user is active (not disabled)."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_api_key(db, api_key: str) -> Optional[UserInDB]:
    """Validate API key and return associated user."""
    # In a real implementation, you would look up the API key in a database
    # For this demo, we're using a simple mapping
    api_keys = {
        "a1b2c3d4e5f6g7h8i9j0": "admin",
        "j9i8h7g6f5e4d3c2b1a0": "moderator",
        "z1x2c3v4b5n6m7k8j9h0": "presenter"
    }
    
    if api_key in api_keys:
        username = api_keys[api_key]
        return get_user(db, username)
    
    return None

# Functions to set up the API security
def setup_api_security(app: FastAPI):
    """Set up the security routes and CORS for the API."""
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi import Request
    
    # Set up CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=SECURITY_CONFIG["ALLOWED_CORS_ORIGINS"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Login endpoint
    @app.post("/token", response_model=Token)
    async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(), 
        request: Request = None
    ):
        # Check rate limits
        client_ip = request.client.host if request else "unknown"
        if not check_rate_limit(form_data.username, client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded"
            )
        
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            logger.warning(f"Failed login attempt for {form_data.username} from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # For the access token, we include the scopes based on the user's roles
        access_token_expires = timedelta(minutes=SECURITY_CONFIG["ACCESS_TOKEN_EXPIRE_MINUTES"])
        access_token = create_access_token(
            data={"sub": user.username, "scopes": user.roles},
            expires_delta=access_token_expires
        )
        
        # For the refresh token, we include only the username
        refresh_token = create_refresh_token(
            data={"sub": user.username}
        )
        
        logger.info(f"Successful login for {user.username} from {client_ip}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    # Refresh token endpoint
    @app.post("/refresh", response_model=Token)
    async def refresh_access_token(
        token: str = Depends(oauth2_scheme),
        request: Request = None
    ):
        client_ip = request.client.host if request else "unknown"
        
        try:
            payload = jwt.decode(
                token, 
                SECURITY_CONFIG["SECRET_KEY"], 
                algorithms=[SECURITY_CONFIG["ALGORITHM"]]
            )
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                )
            
            user = get_user(USERS_DB, username)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )
            
            # Create new tokens
            access_token_expires = timedelta(minutes=SECURITY_CONFIG["ACCESS_TOKEN_EXPIRE_MINUTES"])
            access_token = create_access_token(
                data={"sub": user.username, "scopes": user.roles},
                expires_delta=access_token_expires
            )
            
            refresh_token = create_refresh_token(
                data={"sub": user.username}
            )
            
            logger.info(f"Token refresh for {user.username} from {client_ip}")
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer"
            }
        
        except JWTError:
            logger.warning(f"Invalid refresh token from {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # User info endpoint
    @app.get("/users/me", response_model=User)
    async def read_users_me(current_user: User = Depends(get_current_active_user)):
        return current_user
    
    # Admin user management endpoints would go here in a full implementation

# Function to add a new user programmatically
def add_user(username: str, email: str, password: str, roles: List[str], disabled: bool = False) -> bool:
    """Add a new user to the system."""
    if username in USERS_DB:
        return False
    
    hashed_password = hashlib.sha256((f"{password}{SECURITY_CONFIG['PASSWORD_SALT']}").encode()).hexdigest()
    
    USERS_DB[username] = UserInDB(
        username=username,
        email=email,
        hashed_password=hashed_password,
        roles=roles,
        disabled=disabled
    )
    
    return True

# Function to change a user's password
def change_password(username: str, new_password: str) -> bool:
    """Change a user's password."""
    if username not in USERS_DB:
        return False
    
    hashed_password = hashlib.sha256((f"{new_password}{SECURITY_CONFIG['PASSWORD_SALT']}").encode()).hexdigest()
    USERS_DB[username].hashed_password = hashed_password
    
    return True

# Helper function to require specific roles
def requires_roles(roles: List[str]):
    """Create a dependency that requires specific roles."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ):
        for role in roles:
            if role in current_user.roles:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    return role_checker