# AI Assistant (FastAPI + MongoDB + Gemini)

This project is now a full web application built with **FastAPI** (no Streamlit).  
It includes Google OAuth login/signup, chat history, and RAG-based document Q&A.

## Stack

- FastAPI + Jinja templates + vanilla JS
- MongoDB (users, sessions, conversations, messages, documents)
- Google OAuth2
- Gemini + LangChain + MongoDB Atlas Vector Search

## Run Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set `.env`:
```env
GOOGLE_API_KEY=...
MONGODB_URI=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/callback
APP_SECRET_KEY=replace_with_random_secret
ADMIN_USERNAME=Kotaraju
ADMIN_PASSWORD=Kotaraju
ADMIN_PASSWORD_HASH=
```

3. Start server:
```bash
uvicorn app:app --reload
```

4. Open:
`http://127.0.0.1:8000`

## Admin Routes

- `GET /admin/login` - admin login page
- `POST /admin/login` - admin authenticate
- `GET /admin` - admin dashboard (protected)
- `POST /admin/documents/process` - upload/process docs
- `POST /admin/documents/clear` - clear all indexed docs
- `POST /admin/logout` - admin logout

Default local bypass credentials:
- Username: `Kotaraju`
- Password: `Kotaraju`

## Project Structure

- `app.py` - FastAPI entrypoint and routes
- `web/templates/` - HTML templates (`auth.html`, `chat.html`)
- `web/static/` - UI styles and JS
- `auth/` - OAuth and user/session managers
- `services/` - RAG engine, routing, chat history
- `core/` - config helpers
