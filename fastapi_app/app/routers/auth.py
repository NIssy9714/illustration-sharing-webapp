from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fastapi_app.app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from fastapi_app.app.db.session import get_db
from fastapi_app.app.models import User
from fastapi_app.app.schemas import TokenResponse, UserCreate, UserPublic


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Username already exists")
    db.refresh(user)
    return UserPublic(id=user.id, username=user.username, created_at=user.created_at)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserCreate, db: Session = Depends(get_db)):
    row = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if not row or not verify_password(payload.password, row.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user_id=row.id)
    return TokenResponse(access_token=token)

