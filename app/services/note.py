from fastapi import HTTPException
from app.config import supabase
from app.models import NoteCreate, NoteUpdate

def create_note(note: NoteCreate, user_id: str, token: str):
    try:
        response = supabase.postgrest.auth(token).table("notes").insert({
            "title": note.title,
            "content": note.content,
            "user_id": user_id
        }).execute()
        return {"message": "Note created successfully", 
                "note": response.data[0]
                }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def get_all_notes(limit: int = 20, offset: int = 0):
    try:
        response = supabase.table("notes").select("*").range(offset, offset + limit - 1).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="No notes found")
        return response.data
    except Exception:
        raise 
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def get_user_notes(user_id: str):
    try:
        response = supabase.table("notes").select("*").eq("user_id", user_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="No notes found for this user")
        return response.data
    except Exception:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def update_note(note: NoteUpdate, note_id: str, token: str):
    try:
        update_data = note.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        response = supabase.postgrest.auth(token).table("notes").update(update_data).eq("id", note_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Note not found or no changes made")

        return {"message": "Note updated successfully", 
                "note": response.data[0]
                }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

