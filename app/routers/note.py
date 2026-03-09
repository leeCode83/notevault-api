from fastapi import APIRouter, Depends
from app.models import NoteCreate, NoteUpdate, NoteResponse
from app.routers.auth import get_current_user, oauth2_scheme
from app.services import note as note_service

router = APIRouter()

@router.post("/create")
def create_note(note: NoteCreate, current_user = Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    return note_service.create_note(note, current_user.id, token)

@router.get("/", response_model=list[NoteResponse])
def get_all_notes():
    return note_service.get_all_notes()

@router.get("/user/{user_id}", response_model=list[NoteResponse])
def get_user_notes(user = Depends(get_current_user)):
    return note_service.get_user_notes(user.id)

@router.patch("/update")
def update_note(note: NoteUpdate, token: str = Depends(oauth2_scheme)):
    return note_service.update_note(note, token)
