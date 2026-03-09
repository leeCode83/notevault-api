from fastapi import FastAPI
from app.routers import auth, note

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to Note Vault API"}

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(note.router, prefix="/note", tags=["note"])
