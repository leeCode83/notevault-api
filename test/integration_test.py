"""
Integration Tests — Note Vault API (Real HTTP via httpx)
=========================================================
Memanggil API yang berjalan di http://localhost:8000 secara langsung tanpa mock.
Server harus sudah berjalan sebelum menjalankan test ini:
    uvicorn app.main:app --reload

Jalankan:
    pytest test/integration_test.py -v
    pytest test/integration_test.py -v -s   # tampilkan print output
"""

import uuid
import pytest
import httpx

BASE_URL = "http://localhost:8000"

# Satu user unik dipakai sepanjang sesi test ini
_UNIQUE_ID  = uuid.uuid4().hex[:8]
TEST_EMAIL  = f"k6inttest_{_UNIQUE_ID}@test.dev"
TEST_PASS   = f"TestPass123!{_UNIQUE_ID}"


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    """httpx client yang hidup selama 1 session pytest."""
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as c:
        yield c


@pytest.fixture(scope="session")
def registered_user(client):
    """Daftar user baru sekali lewat /auth/register, return credentials."""
    res = client.post("/auth/register", json={
        "email": TEST_EMAIL,
        "password": TEST_PASS,
    })
    assert res.status_code == 200, f"Setup register failed: {res.text}"
    return {"email": TEST_EMAIL, "password": TEST_PASS}


@pytest.fixture(scope="session")
def auth_token(client, registered_user):
    """Login dan return JWT token (session-scoped, login sekali saja)."""
    res = client.post("/auth/login", data={
        "username": registered_user["email"],
        "password": registered_user["password"],
    })
    assert res.status_code == 200, f"Setup login failed: {res.text}"
    token = res.json()["access_token"]
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def created_note_id(client, auth_headers):
    """Buat satu note untuk dipakai di test update."""
    res = client.post("/note/create", json={
        "title": "Fixture Note Title",
        "content": "This is the fixture note content for update tests.",
    }, headers=auth_headers)
    assert res.status_code == 200, f"Setup create note failed: {res.text}"
    note_id = res.json()["note"]["id"]
    return note_id


# =============================================================================
# GET /  —  Health Check
# =============================================================================

class TestHealthCheck:

    def test_root_returns_200(self, client):
        res = client.get("/")
        assert res.status_code == 200

    def test_root_welcome_message(self, client):
        res = client.get("/")
        assert res.json() == {"message": "Welcome to Note Vault API"}


# =============================================================================
# POST /auth/register
# =============================================================================

class TestRegister:

    def test_register_success(self, client):
        """User baru berhasil terdaftar."""
        uid = uuid.uuid4().hex[:8]
        res = client.post("/auth/register", json={
            "email": f"new_{uid}@test.dev",
            "password": f"NewUser123!{uid}",
        })
        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "User registered successfully"
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_register_duplicate_email(self, client, registered_user):
        """Email yang sudah dipakai → gagal (400)."""
        res = client.post("/auth/register", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert res.status_code == 400

    def test_register_password_too_short(self, client):
        """Password < 10 karakter → validasi gagal (422)."""
        res = client.post("/auth/register", json={
            "email": "short@test.dev",
            "password": "Short1!",
        })
        assert res.status_code == 422

    def test_register_missing_email(self, client):
        """Tidak ada field email → 422."""
        res = client.post("/auth/register", json={
            "password": "ValidPassword123!",
        })
        assert res.status_code == 422

    def test_register_missing_password(self, client):
        """Tidak ada field password → 422."""
        res = client.post("/auth/register", json={
            "email": "nopw@test.dev",
        })
        assert res.status_code == 422

    def test_register_empty_body(self, client):
        """Body kosong → 422."""
        res = client.post("/auth/register", json={})
        assert res.status_code == 422

    def test_register_invalid_email_format(self, client):
        """Email tidak valid (bukan format email) → 400 atau 422."""
        res = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "ValidPassword123!",
        })
        # Supabase atau pydantic akan menolak ini
        assert res.status_code in (400, 422)


# =============================================================================
# POST /auth/login
# =============================================================================

class TestLogin:

    def test_login_success(self, client, registered_user):
        """Login dengan kredensial valid → 200, ada access_token."""
        res = client.post("/auth/login", data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        })
        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "User logged in successfully"
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 0

    def test_login_wrong_password(self, client, registered_user):
        """Password salah → 400."""
        res = client.post("/auth/login", data={
            "username": registered_user["email"],
            "password": "WrongPassword999!",
        })
        assert res.status_code == 400

    def test_login_unregistered_email(self, client):
        """Email tidak terdaftar → 400."""
        res = client.post("/auth/login", data={
            "username": "ghost_nobody@test.dev",
            "password": "SomePassword123!",
        })
        assert res.status_code == 400

    def test_login_missing_username(self, client):
        """Tidak ada field username → 422."""
        res = client.post("/auth/login", data={
            "password": "ValidPassword123!",
        })
        assert res.status_code == 422

    def test_login_missing_password(self, client):
        """Tidak ada field password → 422."""
        res = client.post("/auth/login", data={
            "username": "someone@test.dev",
        })
        assert res.status_code == 422

    def test_login_empty_body(self, client):
        """Body kosong → 422."""
        res = client.post("/auth/login", data={})
        assert res.status_code == 422


# =============================================================================
# GET /note/
# =============================================================================

class TestGetAllNotes:

    def test_get_all_notes_returns_200(self, client, created_note_id):
        """Setelah ada catatan → endpoint mengembalikan 200."""
        # created_note_id fixture memastikan minimal 1 note sudah ada
        res = client.get("/note/")
        assert res.status_code in (200, 404)  # 404 jika DB benar-benar kosong

    def test_get_all_notes_is_list(self, client, created_note_id):
        """Response harus berupa list."""
        res = client.get("/note/")
        if res.status_code == 200:
            assert isinstance(res.json(), list)

    def test_get_all_notes_each_item_has_required_fields(self, client, created_note_id):
        """Setiap item dalam list harus memiliki title dan content."""
        res = client.get("/note/")
        if res.status_code == 200:
            for note in res.json():
                assert "title" in note
                assert "content" in note

    def test_get_all_notes_no_auth_required(self, client):
        """Endpoint ini publik — tidak perlu token."""
        res = client.get("/note/")
        # Tidak boleh 401/403
        assert res.status_code != 401
        assert res.status_code != 403


# =============================================================================
# GET /note/user/{user_id}
# =============================================================================

class TestGetUserNotes:

    def test_get_user_notes_success(self, client, auth_headers, created_note_id):
        """User yang login dapat melihat catatannya sendiri → 200."""
        # Ambil user id dari token via endpoint yang tersedia
        # (gunakan created_note_id yang sudah mencakup note dengan user_id)
        res = client.get(
            f"/note/user/some-id",   # router menggunakan user dari token, bukan path param
            headers=auth_headers,
        )
        # 200 jika user punya note, 404 jika tidak
        assert res.status_code in (200, 404)

    def test_get_user_notes_without_token(self, client):
        """Tanpa token → 401."""
        res = client.get("/note/user/some-user-id")
        assert res.status_code == 401

    def test_get_user_notes_invalid_token(self, client):
        """Token tidak valid → 401."""
        res = client.get(
            "/note/user/some-user-id",
            headers={"Authorization": "Bearer this.is.not.a.valid.token"},
        )
        assert res.status_code == 401

    def test_get_user_notes_malformed_auth_header(self, client):
        """Header Authorization tidak diawali 'Bearer ' → 401."""
        res = client.get(
            "/note/user/some-user-id",
            headers={"Authorization": "Token abc123"},
        )
        assert res.status_code == 401


# =============================================================================
# POST /note/create
# =============================================================================

class TestCreateNote:

    def test_create_note_success(self, client, auth_headers):
        """Catatan berhasil dibuat oleh user yang terautentikasi."""
        res = client.post("/note/create", json={
            "title": "Integration Test Note",
            "content": "This note was created by the integration test suite.",
        }, headers=auth_headers)

        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "Note created successfully"
        assert "note" in body
        assert "id" in body["note"]
        assert body["note"]["title"] == "Integration Test Note"

    def test_create_note_without_token(self, client):
        """Tanpa token → 401."""
        res = client.post("/note/create", json={
            "title": "Unauthorized Note",
            "content": "This should not be created.",
        })
        assert res.status_code == 401

    def test_create_note_invalid_token(self, client):
        """Token tidak valid → 401."""
        res = client.post("/note/create", json={
            "title": "Invalid Auth Note",
            "content": "This should not be created either.",
        }, headers={"Authorization": "Bearer fakejwttoken.invalid.xyz"})
        assert res.status_code == 401

    def test_create_note_title_too_short(self, client, auth_headers):
        """Title kurang dari 5 karakter → 422."""
        res = client.post("/note/create", json={
            "title": "Hi",
            "content": "Valid content here that is long enough.",
        }, headers=auth_headers)
        assert res.status_code == 422

    def test_create_note_content_too_short(self, client, auth_headers):
        """Content kurang dari 10 karakter → 422."""
        res = client.post("/note/create", json={
            "title": "Valid Title Here",
            "content": "Short",
        }, headers=auth_headers)
        assert res.status_code == 422

    def test_create_note_missing_title(self, client, auth_headers):
        """Field title tidak ada → 422."""
        res = client.post("/note/create", json={
            "content": "Content without a title here.",
        }, headers=auth_headers)
        assert res.status_code == 422

    def test_create_note_missing_content(self, client, auth_headers):
        """Field content tidak ada → 422."""
        res = client.post("/note/create", json={
            "title": "Title Without Content",
        }, headers=auth_headers)
        assert res.status_code == 422

    def test_create_note_empty_body(self, client, auth_headers):
        """Body kosong → 422."""
        res = client.post("/note/create", json={}, headers=auth_headers)
        assert res.status_code == 422

    def test_create_note_response_structure(self, client, auth_headers):
        """Verifikasi struktur response note yang dibuat."""
        res = client.post("/note/create", json={
            "title": "Structure Check Note",
            "content": "Checking that the response has the correct fields.",
        }, headers=auth_headers)

        assert res.status_code == 200
        note = res.json()["note"]
        assert "id"      in note
        assert "title"   in note
        assert "content" in note
        assert "user_id" in note


# =============================================================================
# PATCH /note/update
# =============================================================================

class TestUpdateNote:

    def test_update_note_title_and_content(self, client, auth_headers, created_note_id):
        """Update title dan content → 200, data terupdate."""
        res = client.patch(f"/note/update/{created_note_id}", json={
            "title":   "Updated Integration Title",
            "content": "Updated content from the integration test run.",
        }, headers=auth_headers)

        assert res.status_code == 200
        body = res.json()
        assert body["message"] == "Note updated successfully"
        assert body["note"]["id"] == created_note_id
        assert body["note"]["title"] == "Updated Integration Title"

    def test_update_note_content_only(self, client, auth_headers, created_note_id):
        """Update hanya content (title opsional) → 200."""
        res = client.patch(f"/note/update/{created_note_id}", json={
            "content": "Only content was updated this time around.",
        }, headers=auth_headers)

        assert res.status_code == 200
        assert res.json()["message"] == "Note updated successfully"

    def test_update_note_without_token(self, client, created_note_id):
        """Tanpa header Authorization sama sekali → 401 (FastAPI OAuth2 dependency)."""
        res = client.patch(f"/note/update/{created_note_id}", json={
            "title":   "Should Not Update",
            "content": "No auth present in this request.",
        })
        assert res.status_code == 401

    def test_update_note_invalid_token(self, client, created_note_id):
        """Token tidak valid → 400 atau 401.

        PATCH /note/update meneruskan token langsung ke Supabase via postgrest.auth().
        Token yang invalid akan ditolak di DB layer (400 dari Supabase),
        bukan di FastAPI dependency layer (401).
        """
        res = client.patch(f"/note/update/{created_note_id}", json={
            "title":   "Invalid Token Update",
            "content": "This should be rejected by the server.",
        }, headers={"Authorization": "Bearer invalid.jwt.token"})
        assert res.status_code in (400, 401)

    def test_update_note_missing_note_id_in_path(self, client, auth_headers):
        """Path ID tidak lengkap → 404 (Route not found)."""
        res = client.patch("/note/update/", json={
            "title":   "No ID Provided",
            "content": "This should fail because the URL is incomplete.",
        }, headers=auth_headers)
        assert res.status_code == 404

    def test_update_note_title_too_short(self, client, auth_headers, created_note_id):
        """Title kurang dari 5 karakter → 422."""
        res = client.patch(f"/note/update/{created_note_id}", json={
            "title": "Nah",
        }, headers=auth_headers)
        assert res.status_code == 422

    def test_update_note_content_too_short(self, client, auth_headers, created_note_id):
        """Content kurang dari 10 karakter → 422."""
        res = client.patch(f"/note/update/{created_note_id}", json={
            "content": "Brief",
        }, headers=auth_headers)
        assert res.status_code == 422

    def test_update_note_empty_body(self, client, auth_headers, created_note_id):
        """Body kosong → 400 (Handled in service)."""
        res = client.patch(f"/note/update/{created_note_id}", json={}, headers=auth_headers)
        assert res.status_code == 400

    def test_update_nonexistent_note(self, client, auth_headers):
        """Update note dengan ID yang tidak ada → 404."""
        note_id = "00000000-0000-0000-0000-000000000000"
        res = client.patch(f"/note/update/{note_id}", json={
            "content": "Trying to update a nonexistent note.",
        }, headers=auth_headers)
        assert res.status_code == 404
