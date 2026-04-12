import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_host, require_admin, TokenUser
from app.repositories.deck_repository import DeckRepository
from app.schemas.deck import DeckCreate, DeckUpdate, DeckOut, FlashcardIn, FlashcardOut

router = APIRouter(prefix="/decks", tags=["decks"])


def _assert_owner_or_admin(deck_owner_id: uuid.UUID, user: TokenUser):
    if user.role != "admin" and deck_owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your deck")


# ── Deck CRUD ─────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[DeckOut])
async def list_decks(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    if current_user.role == "admin":
        return await repo.get_all()
    return await repo.get_by_owner(current_user.id)


@router.get("/public", response_model=list[DeckOut])
async def list_public_decks(db: AsyncSession = Depends(get_db)):
    repo = DeckRepository(db)
    return await repo.get_public()


@router.get("/{deck_id}", response_model=DeckOut)
async def get_deck(
    deck_id: uuid.UUID,
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    deck = await repo.get_by_id(deck_id)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    if not deck.is_public:
        _assert_owner_or_admin(deck.owner_id, current_user)
    return deck


@router.post("/", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
async def create_deck(
    body: DeckCreate,
    current_user: Annotated[TokenUser, Depends(require_host)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    return await repo.create(
        owner_id=current_user.id,
        title=body.title,
        description=body.description,
        is_public=body.is_public,
    )


@router.patch("/{deck_id}", response_model=DeckOut)
async def update_deck(
    deck_id: uuid.UUID,
    body: DeckUpdate,
    current_user: Annotated[TokenUser, Depends(require_host)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    deck = await repo.get_by_id(deck_id)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    _assert_owner_or_admin(deck.owner_id, current_user)
    return await repo.update(deck, **body.model_dump(exclude_none=True))


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deck(
    deck_id: uuid.UUID,
    current_user: Annotated[TokenUser, Depends(require_host)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    deck = await repo.get_by_id(deck_id, load_cards=False)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    _assert_owner_or_admin(deck.owner_id, current_user)
    await repo.delete(deck)


# ── Flashcard CRUD ────────────────────────────────────────────────────────────

@router.post("/{deck_id}/cards", response_model=FlashcardOut, status_code=status.HTTP_201_CREATED)
async def add_card(
    deck_id: uuid.UUID,
    body: FlashcardIn,
    current_user: Annotated[TokenUser, Depends(require_host)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    deck = await repo.get_by_id(deck_id, load_cards=False)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    _assert_owner_or_admin(deck.owner_id, current_user)
    return await repo.add_card(deck_id, body.term, body.definition, body.position)


@router.patch("/{deck_id}/cards/{card_id}", response_model=FlashcardOut)
async def update_card(
    deck_id: uuid.UUID,
    card_id: uuid.UUID,
    body: FlashcardIn,
    current_user: Annotated[TokenUser, Depends(require_host)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    deck = await repo.get_by_id(deck_id, load_cards=False)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    _assert_owner_or_admin(deck.owner_id, current_user)
    card = await repo.get_card(card_id)
    if not card or card.deck_id != deck_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    return await repo.update_card(card, **body.model_dump(exclude_none=True))


@router.delete("/{deck_id}/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    deck_id: uuid.UUID,
    card_id: uuid.UUID,
    current_user: Annotated[TokenUser, Depends(require_host)],
    db: AsyncSession = Depends(get_db),
):
    repo = DeckRepository(db)
    deck = await repo.get_by_id(deck_id, load_cards=False)
    if not deck:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deck not found")
    _assert_owner_or_admin(deck.owner_id, current_user)
    card = await repo.get_card(card_id)
    if not card or card.deck_id != deck_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
    await repo.delete_card(card)
