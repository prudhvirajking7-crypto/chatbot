# Setup Guide (FastAPI Version)

## 1. Install
```bash
pip install -r requirements.txt
```

## 2. Configure `.env`
```env
GOOGLE_API_KEY=your_gemini_api_key
MONGODB_URI=your_mongodb_uri
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/callback
APP_SECRET_KEY=your_random_long_secret
ADMIN_USERNAME=Kotaraju
ADMIN_PASSWORD=Kotaraju
ADMIN_PASSWORD_HASH=sha256_hash_of_admin_password
```

Generate hash example:
```bash
python -c "import hashlib; print(hashlib.sha256('your_password'.encode()).hexdigest())"
```

## 3. Google OAuth Console

- OAuth client type: **Web application**
- Authorized redirect URIs must include:
  - `http://127.0.0.1:8000/auth/callback`
  - `http://localhost:8000/auth/callback` (optional)

## 4. Run
```bash
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`

Admin login: `http://127.0.0.1:8000/admin/login`

## 5. UI Flow

1. Login/Sign Up page
2. Chat workspace with:
   - Left panel: profile, chat history, knowledge base controls
   - Right panel: messages, mode selector, prompt/response view

## 6. Common Errors

- `redirect_uri_mismatch`: update redirect URI in Google Console exactly.
- `MongoDB URI is required`: set `MONGODB_URI` in `.env`.
- `API Key is required`: set `GOOGLE_API_KEY` in `.env`.
- Admin login fails: set `ADMIN_USERNAME` + `ADMIN_PASSWORD` (or `ADMIN_PASSWORD_HASH`) correctly.
