from fastapi import HTTPException
from app.config import supabase
from app.models import User
from fastapi.security import OAuth2PasswordRequestForm

def verify_token(token: str):
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not hasattr(user_res, 'user') or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user_res.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

def register_user(user: User):
    try:
        response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })
        return {"message": "User registered successfully",
                "access_token": response.session.access_token,
                "token_type": "bearer"
                }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def login_user(form_data: OAuth2PasswordRequestForm):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": form_data.username,
            "password": form_data.password
        })
        return {"message": "User logged in successfully",
                "access_token": response.session.access_token,
                "token_type": "bearer"
                }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
