import uuid
from datetime import datetime

from pydantic import BaseModel


class FlashcardIn(BaseModel):
    term: str
    definition: str
    position: int = 0


class FlashcardOut(BaseModel):
    id: uuid.UUID
    deck_id: uuid.UUID
    term: str
    definition: str
    position: int

    model_config = {"from_attributes": True}


class DeckCreate(BaseModel):
    title: str
    description: str | None = None
    is_public: bool = False


class DeckUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    is_public: bool | None = None


class DeckOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    flashcards: list[FlashcardOut] = []

    model_config = {"from_attributes": True}


class DeckSummary(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    card_count: int = 0

    model_config = {"from_attributes": True}
