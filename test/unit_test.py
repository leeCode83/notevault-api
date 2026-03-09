import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from app.models import User, NoteCreate, NoteUpdate
from app.services.auth import verify_token, register_user, login_user
from app.services.note import create_note, get_all_notes, get_user_notes, update_note
from fastapi.security import OAuth2PasswordRequestForm

# --- MOCKS FOR SUPABASE ---
@pytest.fixture
def mock_supabase():
    with patch("app.services.auth.supabase") as mock_auth_supabase, \
         patch("app.services.note.supabase") as mock_note_supabase:
        yield mock_auth_supabase, mock_note_supabase

# --- TESTS FOR AUTH SERVICE ---

def test_verify_token_success(mock_supabase):
    mock_auth, _ = mock_supabase
    mock_auth.auth.get_user.return_value = MagicMock(user=MagicMock(id="user_123"))
    
    user = verify_token("valid_token")
    assert user.id == "user_123"

def test_verify_token_failure(mock_supabase):
    mock_auth, _ = mock_supabase
    mock_auth.auth.get_user.side_effect = Exception("Invalid JWT")
    
    with pytest.raises(HTTPException) as excinfo:
        verify_token("invalid_token")
    assert excinfo.value.status_code == 401
    assert excinfo.value.detail == "Invalid credentials"

def test_register_user_success(mock_supabase):
    mock_auth, _ = mock_supabase
    mock_auth.auth.sign_up.return_value = MagicMock(session=MagicMock(access_token="new_token"))
    
    user = User(email="test@example.com", password="password123")
    response = register_user(user)
    
    assert response["message"] == "User registered successfully"
    assert response["access_token"] == "new_token"

def test_register_user_failure(mock_supabase):
    mock_auth, _ = mock_supabase
    mock_auth.auth.sign_up.side_effect = Exception("Email already exists")
    
    user = User(email="test@example.com", password="password123")
    with pytest.raises(HTTPException) as excinfo:
        register_user(user)
    assert excinfo.value.status_code == 400

def test_login_user_success(mock_supabase):
    mock_auth, _ = mock_supabase
    mock_auth.auth.sign_in_with_password.return_value = MagicMock(session=MagicMock(access_token="login_token"))
    
    form_data = OAuth2PasswordRequestForm(username="test@example.com", password="password123", scope="")
    response = login_user(form_data)
    
    assert response["message"] == "User logged in successfully"
    assert response["access_token"] == "login_token"

def test_login_user_failure(mock_supabase):
    mock_auth, _ = mock_supabase
    mock_auth.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
    
    form_data = OAuth2PasswordRequestForm(username="test@example.com", password="wrongpassword", scope="")
    with pytest.raises(HTTPException) as excinfo:
        login_user(form_data)
    assert excinfo.value.status_code == 400


# --- TESTS FOR NOTE SERVICE ---

def test_create_note_success(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[{"id": 1, "title": "Test123", "content": "Test content", "user_id": "user_123"}])
    mock_note.postgrest.auth().table().insert.return_value = mock_execute
    
    note = NoteCreate(title="Test123", content="Test content")
    response = create_note(note, "user_123", "valid_token")
    
    assert response["message"] == "Note created successfully"
    assert response["note"]["id"] == 1

def test_create_note_failure(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.side_effect = Exception("Database error")
    mock_note.postgrest.auth().table().insert.return_value = mock_execute
    
    note = NoteCreate(title="Test123", content="Test content")
    with pytest.raises(HTTPException) as excinfo:
        create_note(note, "user_123", "valid_token")
    assert excinfo.value.status_code == 400

def test_get_all_notes_success(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[{"id": 1, "title": "Test"}])
    mock_note.table().select().limit.return_value = mock_execute
    
    response = get_all_notes()
    assert len(response) == 1
    assert response[0]["id"] == 1

def test_get_all_notes_not_found(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[])
    mock_note.table().select().limit.return_value = mock_execute
    
    with pytest.raises(HTTPException) as excinfo:
        get_all_notes()
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "No notes found"

def test_get_user_notes_success(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[{"id": 1, "title": "User Note", "user_id": "user_123"}])
    mock_note.table().select().eq.return_value = mock_execute
    
    response = get_user_notes("user_123")
    assert len(response) == 1
    assert response[0]["user_id"] == "user_123"

def test_get_user_notes_not_found(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[])
    mock_note.table().select().eq.return_value = mock_execute
    
    with pytest.raises(HTTPException) as excinfo:
        get_user_notes("user_unknown")
    assert excinfo.value.status_code == 404
    assert excinfo.value.detail == "No notes found for this user"

def test_update_note_success(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.return_value = MagicMock(data=[{"id": 1, "title": "Updated", "content": "Updated content"}])
    mock_note.postgrest.auth().table().update().eq.return_value = mock_execute
    
    note_update = NoteUpdate(id="1", title="Updated", content="Updated content")
    response = update_note(note_update, "valid_token")
    
    assert response["message"] == "Note updated successfully"
    assert response["note"]["title"] == "Updated"

def test_update_note_failure(mock_supabase):
    _, mock_note = mock_supabase
    mock_execute = MagicMock()
    mock_execute.execute.side_effect = Exception("Update failed")
    mock_note.postgrest.auth().table().update().eq.return_value = mock_execute
    
    note_update = NoteUpdate(id="1", title="Updated", content="Updated content")
    with pytest.raises(HTTPException) as excinfo:
        update_note(note_update, "valid_token")
    assert excinfo.value.status_code == 400
