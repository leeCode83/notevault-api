from pydantic import BaseModel, Field
from typing import Optional

class User(BaseModel):
    email: str
    password: str = Field(..., min_length=10)

class NoteResponse(BaseModel):
    id: Optional[str] = None
    title: str
    content: str
    user_id: Optional[str] = None

class UserNotesResponse(BaseModel):
    user: User
    notes: list[NoteResponse]

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=5)
    content: str = Field(..., min_length=10)

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=5)
    content: Optional[str] = Field(None, min_length=10)

class NoteDelete(BaseModel):
    id: str