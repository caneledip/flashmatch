import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deck import Deck
from app.models.flashcard import Flashcard


class DeckRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, deck_id: uuid.UUID, load_cards: bool = True) -> Deck | None:
        q = select(Deck).where(Deck.id == deck_id)
        if load_cards:
            q = q.options(selectinload(Deck.flashcards))
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def get_by_owner(self, owner_id: uuid.UUID) -> list[Deck]:
        result = await self.db.execute(
            select(Deck)
            .where(Deck.owner_id == owner_id)
            .options(selectinload(Deck.flashcards))
            .order_by(Deck.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_public(self) -> list[Deck]:
        result = await self.db.execute(
            select(Deck)
            .where(Deck.is_public == True)
            .options(selectinload(Deck.flashcards))
            .order_by(Deck.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[Deck]:
        result = await self.db.execute(
            select(Deck)
            .options(selectinload(Deck.flashcards))
            .order_by(Deck.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(
        self, owner_id: uuid.UUID, title: str, description: str | None, is_public: bool
    ) -> Deck:
        deck = Deck(owner_id=owner_id, title=title, description=description, is_public=is_public)
        self.db.add(deck)
        await self.db.commit()
        await self.db.refresh(deck)
        return deck

    async def update(self, deck: Deck, **fields) -> Deck:
        for key, value in fields.items():
            if value is not None:
                setattr(deck, key, value)
        await self.db.commit()
        await self.db.refresh(deck)
        return deck

    async def delete(self, deck: Deck) -> None:
        await self.db.delete(deck)
        await self.db.commit()

    # ── Flashcard operations ──────────────────────────────────────────────────

    async def add_card(
        self, deck_id: uuid.UUID, term: str, definition: str, position: int
    ) -> Flashcard:
        card = Flashcard(deck_id=deck_id, term=term, definition=definition, position=position)
        self.db.add(card)
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def get_card(self, card_id: uuid.UUID) -> Flashcard | None:
        result = await self.db.execute(
            select(Flashcard).where(Flashcard.id == card_id)
        )
        return result.scalar_one_or_none()

    async def update_card(self, card: Flashcard, **fields) -> Flashcard:
        for key, value in fields.items():
            if value is not None:
                setattr(card, key, value)
        await self.db.commit()
        await self.db.refresh(card)
        return card

    async def delete_card(self, card: Flashcard) -> None:
        await self.db.delete(card)
        await self.db.commit()
