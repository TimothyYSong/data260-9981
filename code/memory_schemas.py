from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def utc_now():
    return datetime.now(timezone.utc)


class MessageDocument(BaseModel):
    user_id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime = Field(default_factory=utc_now)


class SummaryDocument(BaseModel):
    user_id: str
    session_id: str | None = None
    scope: Literal["session", "user"]
    text: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.scope == "session" and self.session_id is None:
            raise ValueError("Session summary requires session_id")

        if self.scope == "user" and self.session_id is not None:
            raise ValueError("Lifetime summary must have null session_id")

        return self


class EpisodeDocument(BaseModel):
    user_id: str
    session_id: str
    fact: str
    importance: float = Field(..., ge=0.0, le=1.0)
    embedding: list[float] = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class ChatRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    session_id: str | None = Field(default=None, min_length=1)
    message: str = Field(..., min_length=1)
