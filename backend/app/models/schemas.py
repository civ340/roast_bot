from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class RoastRequest(BaseModel):
    content: str
    user_id: int
    username: str | None = None


class RoastResponse(BaseModel):
    session_id: str
    roast: str
    venom_level: int
    can_escalate: bool
    is_nuclear: bool


class EscalateRequest(BaseModel):
    session_id: str
    user_id: int


class ExcuseRequest(BaseModel):
    situation: str
    user_id: int
    username: str | None = None


class ExcuseResponse(BaseModel):
    session_id: str
    excuse: str
    excuse_level: int
    can_escalate: bool
    is_nuclear: bool


class ConversationRecord(BaseModel):
    id: int
    session_id: UUID
    user_id: int
    role: str
    content: str
    venom_level: int | None
    created_at: datetime
