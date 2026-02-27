# Deploy Guide (FastAPI)

This app is a standard ASGI service. Any platform that supports Python web services works.

## Start Command

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

## Required Environment Variables

```env
GOOGLE_API_KEY=...
MONGODB_URI=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://your-domain/auth/callback
APP_SECRET_KEY=long_random_secret
```

## OAuth Reminder

Add your production callback URL to Google OAuth credentials exactly:

`https://your-domain/auth/callback`
