import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DatabaseSession

from database import get_db
from models import Session as SessionModel
from models import User
from schemas import LoginRequest


router = APIRouter()

SESSION_COOKIE_NAME = "session_token"
SESSION_DURATION_HOURS = 1


@router.post("/login")
def login(
    credentials: LoginRequest,
    response: Response,
    db: DatabaseSession = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == credentials.email)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    password_valid = bcrypt.checkpw(
        credentials.password.encode("utf-8"),
        user.password_hash.encode("utf-8"),
    )

    if not password_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    session_token = secrets.token_urlsafe(32)

    created_at = datetime.utcnow()
    expires_at = created_at + timedelta(
        hours=SESSION_DURATION_HOURS
    )

    session = SessionModel(
        id=session_token,
        user_id=user.id,
        created_at=created_at,
        expires_at=expires_at,
    )

    db.add(session)
    db.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
    )

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }


def get_current_user(
    request: Request,
    db: DatabaseSession = Depends(get_db),
):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)

    if session_token is None:
        raise HTTPException(
            status_code=401,
            detail="Login required",
        )

    session = (
        db.query(SessionModel)
        .filter(SessionModel.id == session_token)
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=401,
            detail="Login required",
        )

    if session.expires_at < datetime.utcnow():
        db.delete(session)
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="Session expired",
        )

    user = (
        db.query(User)
        .filter(User.id == session.user_id)
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Login required",
        )

    return user


@router.get("/me")
def get_logged_in_user(
    user: User = Depends(get_current_user),
):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: DatabaseSession = Depends(get_db),
):
    session_token = request.cookies.get(SESSION_COOKIE_NAME)

    if session_token is not None:
        session = (
            db.query(SessionModel)
            .filter(SessionModel.id == session_token)
            .first()
        )

        if session is not None:
            db.delete(session)
            db.commit()

    response.delete_cookie(SESSION_COOKIE_NAME)

    return {"message": "Logged out"}