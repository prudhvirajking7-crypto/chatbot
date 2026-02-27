import json
import secrets
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from auth.admin_auth import check_credentials
from auth.oauth_manager import AuthManager
from auth.user_manager import UserManager
from core.config import get_config
from services.chat_history import ChatHistoryManager
from services.rag_service import RAGChatbot
from services.response_router import ResponseRouter

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)

app = FastAPI(title="AI Assistant Web App")

secret_key = get_config("APP_SECRET_KEY", "change-this-dev-secret")
app.add_middleware(
    SessionMiddleware,
    secret_key=secret_key,
    session_cookie="chatbot_session",
    same_site="lax",
    https_only=False,
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))
_bot_instance: Optional[RAGChatbot] = None
_bot_last_error: Optional[str] = None
_bot_last_attempt_ts: float = 0.0
_BOT_RETRY_SECONDS = 15.0


@lru_cache(maxsize=1)
def get_auth_manager() -> AuthManager:
    return AuthManager()


@lru_cache(maxsize=1)
def get_user_manager() -> UserManager:
    return UserManager()


@lru_cache(maxsize=1)
def get_history_manager() -> ChatHistoryManager:
    return ChatHistoryManager()


@lru_cache(maxsize=1)
def get_router() -> ResponseRouter:
    return ResponseRouter()


def get_bot() -> Optional[RAGChatbot]:
    global _bot_instance, _bot_last_error, _bot_last_attempt_ts

    if _bot_instance is not None:
        return _bot_instance

    now = time.time()
    if _bot_last_attempt_ts and (now - _bot_last_attempt_ts) < _BOT_RETRY_SECONDS:
        return None

    _bot_last_attempt_ts = now
    try:
        _bot_instance = RAGChatbot()
        _bot_last_error = None
        return _bot_instance
    except Exception as exc:
        _bot_instance = None
        _bot_last_error = f"{type(exc).__name__}: {exc}"
        print(f"rag_init_error: {_bot_last_error}")
        return None


def set_flash(request: Request, message: str, level: str = "info") -> None:
    request.session["flash"] = {"message": message, "level": level}


def pop_flash(request: Request) -> Optional[Dict[str, str]]:
    flash = request.session.pop("flash", None)
    return flash


def get_authenticated_user(request: Request) -> Optional[Dict]:
    session_id = request.session.get("session_id")
    if not session_id:
        return None

    auth_manager = get_auth_manager()
    user_id = auth_manager.validate_session(session_id)
    if not user_id:
        request.session.clear()
        return None

    user_data = auth_manager.get_user(user_id)
    if not user_data:
        request.session.clear()
        return None

    return {"id": user_id, "data": user_data}


def is_admin_authenticated(request: Request) -> bool:
    return bool(request.session.get("admin_authenticated"))


def _format_dt(value) -> str:
    if not value:
        return "-"
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def build_admin_dashboard_data() -> Dict:
    auth_manager = get_auth_manager()
    db = auth_manager.db

    stats = {
        "users": 0,
        "sessions": 0,
        "conversations": 0,
        "messages": 0,
        "documents": 0,
        "db_status": "online",
    }
    recent_users = []
    recent_conversations = []

    try:
        auth_manager.client.admin.command("ping")
    except Exception:
        stats["db_status"] = "offline"
        return {
            "stats": stats,
            "recent_users": recent_users,
            "recent_conversations": recent_conversations,
        }

    try:
        stats["users"] = db["users"].count_documents({})
    except Exception:
        pass

    try:
        stats["sessions"] = db["sessions"].count_documents({})
    except Exception:
        pass

    try:
        stats["conversations"] = db["conversations"].count_documents({})
        stats["messages"] = db["messages"].count_documents({})
    except Exception:
        pass

    try:
        stats["documents"] = db["documents"].count_documents({})
    except Exception:
        pass

    try:
        cursor = (
            db["users"].find(
                {},
                {"name": 1, "email": 1, "last_login": 1},
            )
            .sort("last_login", -1)
            .limit(8)
        )
        recent_users = [
            {
                "name": row.get("name", "Unknown"),
                "email": row.get("email", ""),
                "last_login": _format_dt(row.get("last_login")),
            }
            for row in cursor
        ]
    except Exception:
        recent_users = []

    try:
        cursor = (
            db["conversations"].find(
                {},
                {"title": 1, "user_id": 1, "updated_at": 1},
            )
            .sort("updated_at", -1)
            .limit(10)
        )
        recent_conversations = [
            {
                "title": row.get("title", "New Chat"),
                "user_id": row.get("user_id", "-"),
                "updated_at": _format_dt(row.get("updated_at")),
            }
            for row in cursor
        ]
    except Exception:
        recent_conversations = []

    return {
        "stats": stats,
        "recent_users": recent_users,
        "recent_conversations": recent_conversations,
    }


def ensure_conversation(user_id: str, conversation_id: Optional[str] = None) -> Dict:
    history = get_history_manager()
    conversations = history.get_all_conversations(user_id=user_id)

    if not conversations:
        created_id = history.create_conversation("New Chat", user_id=user_id)
        conversations = history.get_all_conversations(user_id=user_id)
        conversation_id = created_id

    valid_ids = {conv["id"] for conv in conversations}
    if conversation_id not in valid_ids:
        conversation_id = conversations[0]["id"]

    messages = history.get_messages(conversation_id)
    current_title = next(
        (conv["title"] for conv in conversations if conv["id"] == conversation_id),
        "New Chat",
    )

    return {
        "conversations": conversations,
        "conversation_id": conversation_id,
        "messages": messages,
        "current_title": current_title,
    }


def serialize_messages(messages: List[Dict]) -> List[Dict]:
    return [
        {
            "role": msg.get("role", ""),
            "content": msg.get("content", ""),
            "timestamp": msg.get("timestamp").isoformat() if msg.get("timestamp") else "",
        }
        for msg in messages
    ]


def _to_ndjson(event: Dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


def _iter_text_chunks(text: str, chunk_size: int = 80) -> Iterable[str]:
    for idx in range(0, len(text), chunk_size):
        yield text[idx : idx + chunk_size]


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = get_authenticated_user(request)
    if user:
        return RedirectResponse(url="/chat", status_code=302)

    auth_manager = get_auth_manager()
    context = {
        "request": request,
        "flash": pop_flash(request),
        "client_id": auth_manager.client_id,
        "redirect_uri": auth_manager.redirect_uri,
    }
    return templates.TemplateResponse("auth.html", context)


@app.post("/login/local")
def login_local(request: Request, username: str = Form(...), password: str = Form(...)):
    if not check_credentials(username, password):
        set_flash(request, "Invalid login credentials.", "error")
        return RedirectResponse(url="/", status_code=302)

    auth_manager = get_auth_manager()
    local_email = f"{username.lower()}@local.admin"
    local_user_data = {
        "email": local_email,
        "name": f"{username} (Admin)",
        "profile_picture": "",
        "google_id": f"local-admin-{username.lower()}",
    }

    try:
        user_id = auth_manager.create_or_update_user(local_user_data)
        session_id = auth_manager.create_session(user_id, expiry_days=30)

        request.session.clear()
        request.session["session_id"] = session_id
        request.session["admin_authenticated"] = True
        request.session["admin_username"] = username
        set_flash(request, f"Welcome {username}. Logged in successfully.", "success")
        return RedirectResponse(url="/chat", status_code=302)
    except Exception as exc:
        set_flash(request, f"Local login failed: {exc}", "error")
        return RedirectResponse(url="/", status_code=302)


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    if is_admin_authenticated(request):
        return RedirectResponse(url="/admin", status_code=302)

    return templates.TemplateResponse(
        "admin_login.html",
        {
            "request": request,
            "flash": pop_flash(request),
        },
    )


@app.post("/admin/login")
def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if check_credentials(username, password):
        request.session["admin_authenticated"] = True
        request.session["admin_username"] = username
        set_flash(request, "Admin login successful.", "success")
        return RedirectResponse(url="/admin", status_code=302)

    set_flash(request, "Invalid admin credentials.", "error")
    return RedirectResponse(url="/admin/login", status_code=302)


@app.post("/admin/logout")
def admin_logout(request: Request):
    request.session.pop("admin_authenticated", None)
    request.session.pop("admin_username", None)
    set_flash(request, "Logged out from admin.", "info")
    return RedirectResponse(url="/admin/login", status_code=302)


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    dashboard = build_admin_dashboard_data()
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "flash": pop_flash(request),
            "admin_username": request.session.get("admin_username", "admin"),
            "stats": dashboard["stats"],
            "recent_users": dashboard["recent_users"],
            "recent_conversations": dashboard["recent_conversations"],
        },
    )


@app.post("/admin/documents/process")
async def admin_process_documents(request: Request, files: List[UploadFile] = File(default_factory=list)):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    bot = get_bot()
    if not bot:
        set_flash(request, "RAG engine is not initialized. Check API/MongoDB config.", "error")
        return RedirectResponse(url="/admin", status_code=302)

    payloads = []
    for file in files:
        data = await file.read()
        if data:
            payloads.append((file.filename or "uploaded.txt", data))

    if not payloads:
        set_flash(request, "Please select at least one .pdf or .txt file.", "warning")
    else:
        result = bot.process_file_payloads(payloads)
        set_flash(request, result, "success")

    return RedirectResponse(url="/admin", status_code=302)


@app.post("/admin/documents/clear")
def admin_clear_documents(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=302)

    bot = get_bot()
    if not bot:
        set_flash(request, "RAG engine is not initialized.", "error")
    else:
        result = bot.clear_all_documents()
        set_flash(request, result, "success")
    return RedirectResponse(url="/admin", status_code=302)


@app.get("/login/google")
def login_google(request: Request):
    auth_manager = get_auth_manager()
    state_token = secrets.token_urlsafe(24)
    auth_url, oauth_state = auth_manager.get_google_auth_url(state=state_token)
    request.session["oauth_state"] = oauth_state
    return RedirectResponse(url=auth_url, status_code=302)


@app.get("/signup/google")
def signup_google(request: Request):
    auth_manager = get_auth_manager()
    state_token = secrets.token_urlsafe(24)
    auth_url, oauth_state = auth_manager.get_google_auth_url(state=state_token)
    request.session["oauth_state"] = oauth_state
    return RedirectResponse(url=auth_url, status_code=302)


@app.get("/auth/callback")
def auth_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    if error:
        set_flash(request, f"Google authentication failed: {error}", "error")
        return RedirectResponse(url="/", status_code=302)

    if not code:
        set_flash(request, "Missing OAuth code in callback.", "error")
        return RedirectResponse(url="/", status_code=302)

    expected_state = request.session.get("oauth_state")
    if not expected_state or state != expected_state:
        set_flash(request, "Invalid OAuth state. Please try again.", "error")
        return RedirectResponse(url="/", status_code=302)

    auth_manager = get_auth_manager()
    user_data, auth_error = auth_manager.exchange_code_for_token(code, state=state)
    if auth_error or not user_data:
        set_flash(request, auth_error or "Authentication failed.", "error")
        return RedirectResponse(url="/", status_code=302)

    user_id = auth_manager.create_or_update_user(user_data)
    session_id = auth_manager.create_session(user_id)

    request.session.clear()
    request.session["session_id"] = session_id
    return RedirectResponse(url="/chat", status_code=302)


@app.post("/logout")
def logout(request: Request):
    session_id = request.session.get("session_id")
    if session_id:
        get_auth_manager().logout(session_id)
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)


@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, conversation_id: Optional[str] = None):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    context_data = ensure_conversation(user["id"], conversation_id)
    bot = get_bot()
    user_stats = get_user_manager().get_formatted_stats(user["id"])
    is_admin = is_admin_authenticated(request)

    context = {
        "request": request,
        "flash": pop_flash(request),
        "user": user["data"],
        "user_id": user["id"],
        "is_admin": is_admin,
        "user_stats": user_stats,
        "conversations": context_data["conversations"],
        "conversation_id": context_data["conversation_id"],
        "current_title": context_data["current_title"],
        "messages": serialize_messages(context_data["messages"]),
        "doc_count": bot.get_document_count() if bot else 0,
    }
    return templates.TemplateResponse("chat.html", context)


@app.post("/chat/new")
def new_chat(request: Request):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    history = get_history_manager()
    conversation_id = history.create_conversation("New Chat", user_id=user["id"])
    return RedirectResponse(url=f"/chat?conversation_id={conversation_id}", status_code=302)


@app.post("/chat/delete/{conversation_id}")
def delete_chat(request: Request, conversation_id: str):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)

    history = get_history_manager()
    history.delete_conversation(conversation_id)

    conversations = history.get_all_conversations(user_id=user["id"])
    if not conversations:
        created_id = history.create_conversation("New Chat", user_id=user["id"])
        return RedirectResponse(url=f"/chat?conversation_id={created_id}", status_code=302)

    return RedirectResponse(url=f"/chat?conversation_id={conversations[0]['id']}", status_code=302)


@app.post("/documents/process")
async def process_documents(request: Request, files: List[UploadFile] = File(default_factory=list), conversation_id: Optional[str] = Form(default=None)):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    if not is_admin_authenticated(request):
        set_flash(request, "Only admins can manage the Knowledge Base.", "error")
        redirect_to = f"/chat?conversation_id={conversation_id}" if conversation_id else "/chat"
        return RedirectResponse(url=redirect_to, status_code=302)

    bot = get_bot()
    if not bot:
        set_flash(request, "RAG engine is not initialized. Check API/MongoDB config.", "error")
        redirect_to = f"/chat?conversation_id={conversation_id}" if conversation_id else "/chat"
        return RedirectResponse(url=redirect_to, status_code=302)

    payloads = []
    for file in files:
        data = await file.read()
        if data:
            payloads.append((file.filename or "uploaded.txt", data))

    if not payloads:
        set_flash(request, "Please select at least one .pdf or .txt file.", "warning")
    else:
        result = bot.process_file_payloads(payloads)
        set_flash(request, result, "success")

    redirect_to = f"/chat?conversation_id={conversation_id}" if conversation_id else "/chat"
    return RedirectResponse(url=redirect_to, status_code=302)


@app.post("/documents/clear")
def clear_documents(request: Request, conversation_id: Optional[str] = Form(default=None)):
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=302)
    if not is_admin_authenticated(request):
        set_flash(request, "Only admins can clear documents.", "error")
        redirect_to = f"/chat?conversation_id={conversation_id}" if conversation_id else "/chat"
        return RedirectResponse(url=redirect_to, status_code=302)

    bot = get_bot()
    if not bot:
        set_flash(request, "RAG engine is not initialized.", "error")
    else:
        result = bot.clear_all_documents()
        set_flash(request, result, "success")

    redirect_to = f"/chat?conversation_id={conversation_id}" if conversation_id else "/chat"
    return RedirectResponse(url=redirect_to, status_code=302)


class ChatRequest(BaseModel):
    prompt: str
    mode: str = "Auto"
    conversation_id: Optional[str] = None


@app.post("/chat/send/stream")
def send_chat_stream(request: Request, payload: ChatRequest):
    user = get_authenticated_user(request)
    if not user:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    prompt = (payload.prompt or "").strip()
    if not prompt:
        return JSONResponse({"error": "Prompt cannot be empty."}, status_code=400)

    history = get_history_manager()
    conversations = history.get_all_conversations(user_id=user["id"])
    valid_ids = {conv["id"] for conv in conversations}

    conversation_created = False
    conversation_id = payload.conversation_id
    if not conversation_id or conversation_id not in valid_ids:
        conversation_id = history.create_conversation("New Chat", user_id=user["id"])
        conversation_created = True

    existing_messages = history.get_messages(conversation_id)
    history.add_message(conversation_id, "user", prompt)
    if not existing_messages:
        history.auto_generate_title(conversation_id, prompt)

    user_manager = get_user_manager()
    user_manager.increment_message_count(user["id"])
    bot = get_bot()
    router = get_router()

    conversation = history.get_conversation(conversation_id) or {}
    updated_title = conversation.get("title", "New Chat")

    def event_stream():
        answer_parts = []
        source_type = "direct_llm"
        sources = []
        assistant_saved = False
        try:
            yield _to_ndjson(
                {
                    "type": "meta",
                    "conversation_id": conversation_id,
                    "conversation_created": conversation_created,
                    "conversation_title": updated_title,
                }
            )

            if not bot:
                chunk_iter = _iter_text_chunks("Knowledge base is not initialized. Check API key and MongoDB settings.")
                source_type = "direct_llm"
                sources = []
            else:
                doc_count = bot.get_document_count()
                chunk_iter, source_type, sources = router.route_query_stream(
                    query=prompt,
                    mode=payload.mode,
                    bot=bot,
                    doc_count=doc_count,
                )

            for chunk in chunk_iter:
                if not chunk:
                    continue
                answer_parts.append(chunk)
                yield _to_ndjson({"type": "chunk", "content": chunk})

            answer = "".join(answer_parts).strip()
            if not answer:
                answer = "I could not generate a response. Please try again."
                yield _to_ndjson({"type": "chunk", "content": answer})

            history.add_message(conversation_id, "assistant", answer)
            assistant_saved = True
            user_manager.increment_token_usage(user["id"], max(len(answer) // 4, 1))

            source_display = router.get_source_display(source_type, len(sources))
            source_preview = [doc.page_content[:220] for doc in sources[:3]] if sources else []

            yield _to_ndjson(
                {
                    "type": "done",
                    "conversation_id": conversation_id,
                    "conversation_created": conversation_created,
                    "conversation_title": updated_title,
                    "source_display": source_display,
                    "source_type": source_type,
                    "source_preview": source_preview,
                }
            )
        except Exception as exc:
            print(f"chat_stream_error: {exc}")
            interrupted_note = "\n\n[Generation interrupted. Please try again.]"
            if answer_parts:
                answer_parts.append(interrupted_note)
                yield _to_ndjson({"type": "chunk", "content": interrupted_note})
                final_answer = "".join(answer_parts).strip()
            else:
                final_answer = "Internal server error while generating response. Check backend logs/config."
                yield _to_ndjson({"type": "chunk", "content": final_answer})

            if not assistant_saved:
                history.add_message(conversation_id, "assistant", final_answer)
                user_manager.increment_token_usage(user["id"], max(len(final_answer) // 4, 1))

            yield _to_ndjson({"type": "error", "error": "Internal server error while generating response."})

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post("/chat/send")
def send_chat(request: Request, payload: ChatRequest):
    try:
        user = get_authenticated_user(request)
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        prompt = (payload.prompt or "").strip()
        if not prompt:
            return JSONResponse({"error": "Prompt cannot be empty."}, status_code=400)

        history = get_history_manager()
        conversations = history.get_all_conversations(user_id=user["id"])
        valid_ids = {conv["id"] for conv in conversations}

        conversation_created = False
        conversation_id = payload.conversation_id
        if not conversation_id or conversation_id not in valid_ids:
            conversation_id = history.create_conversation("New Chat", user_id=user["id"])
            conversation_created = True

        existing_messages = history.get_messages(conversation_id)
        history.add_message(conversation_id, "user", prompt)
        if not existing_messages:
            history.auto_generate_title(conversation_id, prompt)

        bot = get_bot()
        user_manager = get_user_manager()
        user_manager.increment_message_count(user["id"])

        if not bot:
            answer = "Knowledge base is not initialized. Check API key and MongoDB settings."
            source_type = "direct_llm"
            sources = []
        else:
            doc_count = bot.get_document_count()
            answer, source_type, sources = get_router().route_query(
                query=prompt,
                mode=payload.mode,
                bot=bot,
                doc_count=doc_count,
            )

        history.add_message(conversation_id, "assistant", answer)
        user_manager.increment_token_usage(user["id"], max(len(answer) // 4, 1))

        source_display = get_router().get_source_display(source_type, len(sources))
        source_preview = [doc.page_content[:220] for doc in sources[:3]] if sources else []

        conversation = history.get_conversation(conversation_id) or {}
        updated_title = conversation.get("title", "New Chat")
        return JSONResponse(
            {
                "conversation_id": conversation_id,
                "conversation_created": conversation_created,
                "conversation_title": updated_title,
                "response": answer,
                "source_display": source_display,
                "source_type": source_type,
                "source_preview": source_preview,
            }
        )
    except Exception as exc:
        print(f"chat_send_error: {exc}")
        return JSONResponse(
            {"error": "Internal server error while generating response. Check backend logs/config."},
            status_code=500,
        )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/favicon.svg", status_code=307)
