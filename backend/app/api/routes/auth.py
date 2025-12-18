from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.app.core import security
from backend.app.core.config import settings
from backend.app.db import models
from backend.app.schemas import TokenResponse, UserCreate, UserRead
from backend.app.api.deps import get_db_session, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
def register(user_in: UserCreate, db: Session = Depends(get_db_session)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    user = models.User(email=user_in.email, hashed_password=security.get_password_hash(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db_session)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = security.create_token(
        subject=user.email, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = security.create_token(
        subject=user.email, expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes)
    )

    db.add(models.RefreshToken(user_id=user.id, token=refresh_token))
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(token: str, db: Session = Depends(get_db_session)):
    email = security.decode_token(token)
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    record = db.query(models.RefreshToken).filter(models.RefreshToken.token == token).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")

    access_token = security.create_token(
        subject=email, expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    refresh_token = security.create_token(
        subject=email, expires_delta=timedelta(minutes=settings.refresh_token_expire_minutes)
    )
    record.token = refresh_token
    db.commit()
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserRead)
def me(current_user: models.User = Depends(get_current_user)):
    return current_user
