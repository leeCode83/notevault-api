from fastapi import APIRouter, Depends, Request
from fastapi_cache.decorator import cache
from app.models import NoteCreate, NoteUpdate, NoteResponse
from app.routers.auth import get_current_user, oauth2_scheme
from app.services import note as note_service
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter()

@router.post("/create")
def create_note(note: NoteCreate, current_user = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    return note_service.create_note(note, current_user.id, token)

@router.get("/", response_model=list[NoteResponse])
@limiter.limit("100/minute")
@cache(expire=300)
def get_all_notes(request: Request, limit: int = 20, offset: int = 0):
    return note_service.get_all_notes(limit, offset)

@router.get("/user/{user_id}", response_model=list[NoteResponse])
@limiter.limit("100/minute")
@cache(expire=300)
def get_user_notes(request: Request, user_id: str, user = Depends(get_current_user)):
    return note_service.get_user_notes(user.id)

@router.patch("/update/{note_id}")
def update_note(note: NoteUpdate, note_id: str, token: str = Depends(oauth2_scheme)):
    return note_service.update_note(note, note_id, token)
