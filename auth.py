from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status
from database import SessionLocal
from models import Users
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
)


bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class CreateUserRequest(BaseModel):
    username: str
    password: str
    target_calorie: int = 2000   # optional — defaults to 2000 kcal

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshRequest(BaseModel):
    refresh_token: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

def authenticate_user(username: str, password: str, db):
    user = db.query(Users).filter(Users.username == username).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int, user_role: str, expires_delta: timedelta):
    encode = {"sub": username, "id": user_id, "role": user_role, "type": "access"}
    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({"exp": int(expires.timestamp())})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(username: str, user_id: int, user_role: str):
    """Long-lived token (7 days) — used only by POST /auth/refresh."""
    encode = {"sub": username, "id": user_id, "role": user_role, "type": "refresh"}
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    encode.update({"exp": int(expires.timestamp())})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str  = payload.get("sub")
        user_id: int   = payload.get("id")
        user_role: str = payload.get("role")
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user")
        return {"username": username, "id": user_id, "role": user_role}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate user")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    existing_user = db.query(Users).filter(Users.username == create_user_request.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    create_user_model = Users(
        username=create_user_request.username,
        hashed_password=bcrypt_context.hash(create_user_request.password),
        target_calorie=create_user_request.target_calorie
    )
    db.add(create_user_model)
    db.commit()
    return {"message": "User created successfully", "username": create_user_request.username}


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    token   = create_access_token(user.username, user.id, user.role, timedelta(minutes=30))
    refresh = create_refresh_token(user.username, user.id, user.role)
    return {"access_token": token, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh_access_token(request: RefreshRequest):
    """
    Exchange a valid refresh token for a brand-new access + refresh token pair.
    The old refresh token is consumed; a fresh 7-day one is issued.
    """
    try:
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        # Guard: reject access tokens being used here
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        username: str  = payload.get("sub")
        user_id: int   = payload.get("id")
        user_role: str = payload.get("role")
        if username is None or user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        new_access  = create_access_token(username, user_id, user_role, timedelta(minutes=30))
        new_refresh = create_refresh_token(username, user_id, user_role)
        return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid — please log in again"
        )


user_dependency_auth = Annotated[dict, Depends(get_current_user)]

@router.put("/password/")
async def change_password(request: ChangePasswordRequest, user: user_dependency_auth, db: db_dependency):
    """Change the logged-in user's password after verifying their current one."""
    db_user = db.query(Users).filter(Users.id == user['id']).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not bcrypt_context.verify(request.current_password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    db_user.hashed_password = bcrypt_context.hash(request.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

