from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from app.models import User
from app.services import auth as auth_service

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    return auth_service.verify_token(token)

@router.post("/register")
def register(user: User):
    return auth_service.register_user(user)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return auth_service.login_user(form_data)