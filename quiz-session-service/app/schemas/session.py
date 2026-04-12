import uuid
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    deck_id: uuid.UUID
    question_time_limit: int = 20


class CreateSessionResponse(BaseModel):
    pin: str
    deck_id: uuid.UUID
    question_time_limit: int


class SessionStatusResponse(BaseModel):
    pin: str
    status: str
    player_count: int
    current_question_index: int
